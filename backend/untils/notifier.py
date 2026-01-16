import json
import os
import logging
from datetime import datetime

from pywebpush import webpush, WebPushException

import untils.db_multi as dbM
from untils.parser import parse
from untils import subcription

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
BOT_ONLINE = os.getenv("BOT_ONLINE", "false").lower() == "true"

log = logging.getLogger(__name__)

notified_slots = set()


def _cleanup_notified(current_date):
    prefix = current_date.strftime("%Y-%m-%d")
    stale = [key for key in notified_slots if not key.startswith(prefix)]
    for key in stale:
        notified_slots.discard(key)


def _slot_key(current_date, queue, hour, minute=None):
    queue_code = subcription.queue_code_from_input(queue)
    queue_lbl = subcription.queue_label(queue_code)
    time_part = f"{hour:02d}" if minute is None else f"{hour:02d}:{minute:02d}"
    return f"{current_date.strftime('%Y-%m-%d')}-q{queue_lbl}-{time_part}"


def _hour_state(status, hour):
    if not status or hour < 0:
        return None

    total = len(status)
    if total >= 48:
        if hour >= 24 or hour * 2 >= total:
            return None
        start = hour * 2
        end = min(start + 2, total)
        block = status[start:end]
        return 1 if any(block) else 0

    if total >= 24:
        idx = min(hour, total - 1)
        return 1 if status[idx] else 0

    idx = min(hour * 2, total - 1)
    return 1 if status[idx] else 0


async def parse_status_for_queue(queue_code: int):
    label = subcription.queue_label(queue_code)
    try:
        return await parse(queue_code)
    except Exception as exc:
        log.error("parse failed for queue %s, %s: %s", queue_code, label, exc)
        return []


async def load_subscriptions_from_storage(force_db: bool = False):
    await subcription.load_subscriptions_from_storage(force_db=force_db)


async def save_all_to_redis():
    await subcription.save_all_to_redis()


async def _send_telegram_notifications(text: str, queue: int | None = None):
    if not BOT_ONLINE:
        return 0, []

    try:
        from bot.untils.notifier import send_notify
    except Exception as exc:
        log.warning("Telegram notifier unavailable: %s", exc)
        return 0, [str(exc)]

    tg_subs = subcription.get_telegram_subs(queue)
    sent = 0
    errors: list[str] = []

    for sub in tg_subs:
        tg_id = (sub or {}).get("id") or (sub or {}).get("tg_id")
        if tg_id is None:
            continue
        try:
            await send_notify(int(tg_id), text)
            sent += 1
        except Exception as exc:
            log.warning("Telegram notify failed for %s: %s", tg_id, exc)
            await dbM.delete_tg_sub(tg_id)
            errors.append(f"{tg_id}: {exc}")

    return sent, errors


async def notify_all(title: str, message: str):
    sent = 0
    errors: list[str] = []

    for raw in subcription.get_push_subs():
        sub = subcription.normalize_subscription(raw)
        if not sub:
            continue

        endpoint = sub.get("endpoint", "")

        try:
            webpush(
                subscription_info=sub,
                data=json.dumps({"title": title, "body": message}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": "mailto:kostantinreksa@gmail.com"},
            )
            sent += 1

        except WebPushException as ex:
            status_code = getattr(getattr(ex, "response", None), "status_code", None)
            log.warning("Push failed for %s...: %s (status=%s)", endpoint[:80], ex, status_code)

            if status_code in (404, 410):
                await dbM.delete_web_sub(endpoint)
                continue

            errors.append(f"{endpoint[:80]}...: {ex}")

        except Exception as ex:
            log.error("Unexpected push error for %s...: %s", endpoint[:80], ex)
            errors.append(f"{endpoint[:80]}...: {ex}")

    tg_sent, tg_errors = await _send_telegram_notifications(f"{title}\n{message}")

    return {"sent": sent, "errors": errors, "tg_sent": tg_sent, "tg_errors": tg_errors}


async def check_and_notify():
    try:
        now = datetime.now()
        _cleanup_notified(now.date())

        for queue_code, queue_subs in list(subcription.push_subscriptions.items()):
            if not queue_subs:
                continue

            try:
                status = await parse_status_for_queue(queue_code)
            except Exception as parse_err:
                log.error("Failed to parse queue %s: %s", queue_code, parse_err)
                continue

            await _process_queue_schedule(queue_code, status, now)

    except Exception as e:
        log.error("check_and_notify failed: %s", e)


async def _process_queue_schedule(queue: int, status: list[int] | None, now: datetime):
    if not status:
        return

    queue_lbl = subcription.queue_label(queue)

    if len(status) >= 48:
        current_slot = now.hour * 2 + (1 if now.minute >= 30 else 0)
        if current_slot >= len(status):
            return

        last_slot_to_check = min(len(status) - 1, current_slot + 2)  # look ahead ~1h
        prev_state = 1 if status[current_slot] else 0

        for slot_idx in range(current_slot + 1, last_slot_to_check + 1):
            state = 1 if status[slot_idx] else 0
            if prev_state == 0 and state == 1:
                target_hour = slot_idx // 2
                target_minute = 30 if slot_idx % 2 else 0
                slot_id = _slot_key(now.date(), queue, target_hour, target_minute)

                if slot_id not in notified_slots:
                    await send_push_all(
                        title="Скоро відключать світло",
                        body=(
                            f"По графіку (черга {queue_lbl}) світло відключать в "
                            f"{target_hour:02d}:{target_minute:02d}."
                        ),
                        queue=queue,
                    )
                    notified_slots.add(slot_id)
                break

            prev_state = state
        return

    current_hour = now.hour
    next_hour = current_hour + 1

    current_state = _hour_state(status, current_hour)
    next_state = _hour_state(status, next_hour)
    slot_id = _slot_key(now.date(), queue, next_hour)

    if current_state == 0 and next_state == 1 and slot_id not in notified_slots:
        await send_push_all(
            title="Скоро відключать світло",
            body=f"По графіку (черга {queue_lbl}) світло відключать в {next_hour:02d}:00.",
            queue=queue,
        )
        notified_slots.add(slot_id)


async def send_push_all(title: str, body: str, queue: int):
    target_queue = subcription.queue_code_from_input(queue)
    subs = list(subcription.get_push_subs(target_queue))

    sent = 0
    for raw in subs:
        try:
            sub = subcription.normalize_subscription(raw)
            if not sub:
                continue
            webpush(
                subscription_info=sub,
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": "mailto:kostantinreksa@gmail.com"},
            )
            sent += 1
        except Exception as ex:
            log.warning("Push failed: %s", ex)
    tg_sent, tg_errors = await _send_telegram_notifications(f"{title}\n{body}", target_queue)

    if tg_errors:
        log.warning("Telegram notify errors for queue %s: %s", target_queue, tg_errors)

    log.info(
        "Notifications sent for queue %s: push=%s tg=%s",
        subcription.queue_label(target_queue),
        sent,
        tg_sent,
    )
