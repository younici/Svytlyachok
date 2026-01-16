import json
import re
import logging
from typing import Dict, List, Tuple, Optional, Any

import untils.redis_db as redis_un
import db.orm.utils as db
from db.orm.session import AsyncSessionLocal
from db.orm.models import Subscription
from sqlalchemy import select

from untils.variebles import QUEUE_LABELS

log = logging.getLogger(__name__)

# In-memory storages
push_subscriptions: Dict[int, List[dict]] = {}
telegram_subscriptions: Dict[int, List[dict]] = {}

_redis_client = None

def set_redis_client(client):
    global _redis_client
    _redis_client = client


def queue_code_from_input(value) -> int:
    default_queue = 11
    if value is None:
        return default_queue

    raw = value
    if isinstance(raw, str):
        raw = raw.strip()

        match = re.match(r"^([1-6])\.([12])$", raw)
        if match:
            code = int(match.group(1)) * 10 + int(match.group(2))
            return code if code in QUEUE_LABELS else default_queue

        try:
            if "." in raw:
                raw_numeric = float(raw)
            else:
                raw_numeric = int(raw)
        except (TypeError, ValueError):
            raw_numeric = None
    else:
        raw_numeric = raw

    if isinstance(raw_numeric, float):
        if raw_numeric.is_integer():
            raw_numeric = int(raw_numeric)
        else:
            major = int(raw_numeric)
            minor = int(round((raw_numeric - major) * 10))
            code = major * 10 + minor
            return code if code in QUEUE_LABELS else default_queue

    try:
        numeric = int(raw_numeric)
    except (TypeError, ValueError):
        return default_queue

    return numeric if numeric in QUEUE_LABELS else default_queue


def queue_label(queue_code: int) -> str:
    return QUEUE_LABELS.get(queue_code, str(queue_code))


def get_push_subs(queue: Optional[int] = None) -> List[dict]:
    if queue is None:
        combined = []
        for bucket in push_subscriptions.values():
            combined.extend(bucket)
        return combined

    queue_code = queue_code_from_input(queue)
    return push_subscriptions.get(queue_code, [])


def find_push_subscription(endpoint: str) -> Tuple[Optional[int], Optional[int]]:
    for queue_id, bucket in push_subscriptions.items():
        for idx, item in enumerate(bucket):
            if (item or {}).get("endpoint") == endpoint:
                return queue_id, idx
    return None, None


def remember_push_subscription(sub_data: dict):
    queue = queue_code_from_input(sub_data.get("queue"))
    sub_data["queue"] = queue
    push_subscriptions.setdefault(queue, []).append(sub_data)


def forget_push_subscription(endpoint: str):
    if not endpoint:
        return False
    for queue_id, bucket in list(push_subscriptions.items()):
        for idx, item in enumerate(bucket):
            if (item or {}).get("endpoint") == endpoint:
                try:
                    bucket.pop(idx)
                except Exception:
                    pass
                return True
    return False


def normalize_tg_subscription(sub: Any):
    if not sub:
        return None

    if isinstance(sub, str):
        try:
            sub = json.loads(sub)
        except json.JSONDecodeError:
            return None

    tg_id = None
    queue_id = None

    if isinstance(sub, dict):
        tg_id = sub.get("tg_id") or sub.get("id")
        queue_id = sub.get("queue") if sub.get("queue") is not None else sub.get("queue_id")
    else:
        tg_id = getattr(sub, "tg_id", None)
        queue_id = getattr(sub, "queue_id", None)

    if tg_id is None:
        return None

    queue_code = queue_code_from_input(queue_id)
    try:
        tg_numeric = int(tg_id)
    except (TypeError, ValueError):
        return None

    return {"id": tg_numeric, "queue": queue_code}


def remember_telegram_subscription(sub_data: dict):
    normalized = normalize_tg_subscription(sub_data)
    if not normalized:
        return

    forget_telegram_subscription(normalized["id"])

    queue = normalized["queue"]
    telegram_subscriptions.setdefault(queue, []).append(normalized)


def get_telegram_subs(queue: Optional[int] = None) -> List[dict]:
    if queue is None:
        combined = []
        for bucket in telegram_subscriptions.values():
            combined.extend(bucket)
        return combined

    queue_code = queue_code_from_input(queue)
    return telegram_subscriptions.get(queue_code, [])


def forget_telegram_subscription(identifier: int):
    removed = False
    for queue_id, bucket in list(telegram_subscriptions.items()):
        filtered = [item for item in bucket if (item or {}).get("id") != identifier]
        if len(filtered) != len(bucket):
            telegram_subscriptions[queue_id] = filtered
            removed = True
    return removed


def normalize_subscription(sub: Any):
    if not sub:
        return None

    if isinstance(sub, str):
        try:
            sub = json.loads(sub)
        except json.JSONDecodeError:
            return None

    endpoint = None
    p256dh = None
    auth = None
    queue_id = None

    if hasattr(sub, "endpoint"):
        endpoint = getattr(sub, "endpoint", None)
        p256dh = getattr(sub, "p256dh", None)
        auth = getattr(sub, "auth", None)

        queue_id = getattr(sub, "queue_id", None)
    elif isinstance(sub, dict):
        endpoint = sub.get("endpoint")
        queue_id = sub.get("queue")
        if queue_id is None:
            queue_id = sub.get("queue_id")
        keys = sub.get("keys") or {}
        p256dh = keys.get("p256dh") or sub.get("p256dh")
        auth = keys.get("auth") or sub.get("auth")

    if not endpoint or not p256dh or not auth:
        return None

    queue_id = queue_code_from_input(queue_id)

    normalized = {
        "endpoint": endpoint,
        "keys": {
            "p256dh": p256dh,
            "auth": auth
        },
        "queue": queue_id,
    }

    return normalized


def replace_push_subscriptions(raw_subscriptions: List[Any]):
    global push_subscriptions
    push_subscriptions = {}
    for item in raw_subscriptions:
        normalized = normalize_subscription(item)
        if normalized:
            remember_push_subscription(normalized)


def replace_telegram_subscriptions(raw_subscriptions: List[Any]):
    global telegram_subscriptions
    telegram_subscriptions = {}
    for item in raw_subscriptions:
        remember_telegram_subscription(item)


async def save_subscription_db(queue: int, sub_payload: dict):
    if AsyncSessionLocal is None:
        log.warning("save_subscription_db(): DB not available, skipping.")
        return False

    endpoint = sub_payload.get("endpoint")
    keys = sub_payload.get("keys") or {}
    p256dh = keys.get("p256dh") or sub_payload.get("p256dh")
    auth = keys.get("auth") or sub_payload.get("auth")

    if not endpoint or not p256dh or not auth:
        log.warning("save_subscription_db(): invalid data %s", sub_payload)
        return False

    async with AsyncSessionLocal() as session:
        try:
            stmt = select(Subscription).where(Subscription.endpoint == endpoint)
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()

            if existing:
                existing.p256dh = p256dh
                existing.auth = auth
                existing.queue_id = queue

                await session.commit()
                return existing.id

            new_sub = Subscription(
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                queue_id=queue,
            )
            session.add(new_sub)
            await session.commit()

            log.info("Subscription saved: %s...", endpoint[:50])
            return new_sub.id

        except Exception:
            await session.rollback()
            raise


async def save_all_to_redis():
    global _redis_client
    if not _redis_client:
        return

    try:
        await redis_un.save_push_subscriptions(list(get_push_subs()))
        await redis_un.save_tg_subscriptions(list(get_telegram_subs()))
    except Exception as exc:
        log.warning("Redis sync failed, disabling cache: %s", exc)
        _redis_client = None


async def load_subscriptions_from_storage(force_db: bool = False):
    global push_subscriptions, telegram_subscriptions, _redis_client

    push_subscriptions = {}
    telegram_subscriptions = {}
    loaded = False

    if _redis_client and not force_db:
        try:
            loaded = await redis_un.load_all_into_subcription()
        except Exception as exc:
            log.warning("Failed to load subscriptions from Redis, disabling cache: %s", exc)
            _redis_client = None

    if loaded:
        return

    log.info("Loading subscriptions from DB (Redis unavailable or force_db=True).")

    db_subs = await db.get_all_http_sub()
    replace_push_subscriptions(db_subs or [])

    tg_db_subs = await db.get_all_tg_subscribers()
    replace_telegram_subscriptions([{"id": sub.tg_id, "queue": sub.queue_id} for sub in tg_db_subs or []])

    if _redis_client:
        await save_all_to_redis()


async def remove_push_subscription(endpoint: str):
    """Forget push subscription, delete from DB and sync cache."""
    if not endpoint:
        return False

    removed = forget_push_subscription(endpoint)

    try:
        await db.delete_sub(endpoint)
    except Exception as ex:
        log.warning("delete_sub failed for %s...: %s", endpoint[:80], ex)

    await save_all_to_redis()
    return removed
