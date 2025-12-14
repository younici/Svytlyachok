import json
import re
import logging
from typing import Dict, List, Tuple, Optional, Any

import untils.redis_db as redis_un
import db.orm.utils as db
from db.orm.session import AsyncSessionLocal
from db.orm.models.subscription import Subscription
from db.orm.models.user import User
from sqlalchemy import select

from untils.variebles import QUEUE_LABELS

log = logging.getLogger(__name__)

# In-memory storages
push_subscriptions: Dict[int, List[dict]] = {}
telegram_subscriptions: Dict[int, List[dict]] = {}

_redis_client = None

# Queue labels map

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
        if queue_id is None:
            try:
                user = getattr(sub, "user", None)
            except Exception:
                user = None
            if user is not None:
                queue_id = getattr(user, "queue_id", None)
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
            stmt = (
                select(Subscription, User)
                .join(User, Subscription.user_id == User.id, isouter=True)
                .where(Subscription.endpoint == endpoint)
            )
            res = await session.execute(stmt)
            row = res.first()

            if row:
                existing, user = row
                existing.p256dh = p256dh
                existing.auth = auth

                if user:
                    user.queue_id = queue
                else:
                    new_user = User(queue_id=queue)
                    session.add(new_user)
                    await session.flush()
                    existing.user_id = new_user.id

                await session.commit()
                return existing.user_id

            user = User(queue_id=queue)
            session.add(user)
            await session.flush()

            new_sub = Subscription(
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                user_id=user.id,
            )
            session.add(new_sub)
            await session.commit()

            log.info("Subscription saved: %s...", endpoint[:50])
            return new_sub.user_id

        except Exception:
            await session.rollback()
            raise


async def save_all_to_redis():
    global _redis_client
    if not _redis_client:
        return

    try:
        all_subs = [json.dumps(sub) for sub in get_push_subs() if sub]

        await _redis_client.delete("subscriptions")

        if all_subs:
            await _redis_client.rpush("subscriptions", *all_subs)

        log.info("Synced subscriptions to Redis: %s", len(all_subs))
    except Exception as exc:
        log.warning("Redis sync failed, disabling cache: %s", exc)
        _redis_client = None


async def load_subscriptions_from_storage(force_db: bool = False):
    global push_subscriptions, _redis_client

    push_subscriptions = {}
    subs_data = None

    if _redis_client and not force_db:
        try:
            subs_data = await redis_un.load_push_subscriptions_raw()
        except Exception as exc:
            log.warning("Failed to load subscriptions from Redis, disabling cache: %s", exc)
            _redis_client = None

    if subs_data:
        loaded = 0
        for item in subs_data:
            normalized = normalize_subscription(item)
            if not normalized:
                continue
            remember_push_subscription(normalized)
            loaded += 1
        log.info("Loaded subscriptions from Redis: %s", loaded)
        return

    log.info("Subscriptions not found in Redis, falling back to DB.")
    db_subs = await db.get_all_http_sub()
    loaded = 0
    for item in db_subs or []:
        normalized = normalize_subscription(item)
        if not normalized:
            continue
        remember_push_subscription(normalized)
        loaded += 1
    if not loaded:
        log.info("No subscriptions found in the database.")
    else:
        log.info("Loaded subscriptions from database: %s", loaded)
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


# Placeholders for future Telegram subscription handlers
def remember_telegram_subscription(sub_data: dict):
    queue = queue_code_from_input(sub_data.get("queue"))
    sub_data["queue"] = queue
    telegram_subscriptions.setdefault(queue, []).append(sub_data)


def get_telegram_subs(queue: Optional[int] = None) -> List[dict]:
    if queue is None:
        combined = []
        for bucket in telegram_subscriptions.values():
            combined.extend(bucket)
        return combined
    queue_code = queue_code_from_input(queue)
    return telegram_subscriptions.get(queue_code, [])


def forget_telegram_subscription(identifier: str):
    for queue_id, bucket in list(telegram_subscriptions.items()):
        for idx, item in enumerate(bucket):
            if item.get("id") == identifier:
                try:
                    bucket.pop(idx)
                except Exception:
                    pass
                return True
    return False
