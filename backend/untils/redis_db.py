import json
import os
import logging

import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)


_redis_client: redis.Redis | None = None


async def init_redis() -> redis.Redis | None:
    global _redis_client

    redis_url = os.getenv("REDIS_URL")

    if not redis_url:
        return None

    _redis_client = redis.from_url(redis_url)

    try:
        await _redis_client.ping()
    except Exception as e:
        log.error(e)
        _redis_client = None

    return _redis_client


def get_redis_client() -> redis.Redis | None:
    return _redis_client


async def save_push_subscriptions(subscriptions: list[dict]) -> bool:
    """Persist HTTP push subscriptions to Redis list."""
    if not _redis_client:
        return False

    payload = [json.dumps(item) for item in subscriptions if item]
    await _redis_client.delete("subscriptions")

    if payload:
        await _redis_client.rpush("subscriptions", *payload)

    log.info("Saved %s push subscriptions to Redis", len(payload))
    return True


async def save_tg_subscription(tg_id: int, queue_id: int) -> bool:
    """Save or update a single Telegram subscriber in Redis hash."""
    if not _redis_client:
        return False

    data = json.dumps({"id": int(tg_id), "queue": int(queue_id)})
    await _redis_client.hset("tg_subscriptions", tg_id, data)
    return True


async def save_tg_subscriptions(subscriptions: list[dict]) -> bool:
    """Persist Telegram subscribers to Redis hash."""
    if not _redis_client:
        return False

    if not subscriptions:
        await _redis_client.delete("tg_subscriptions")
        log.info("Saved 0 telegram subscriptions to Redis")
        return True

    mapping = {str(item.get("id")): json.dumps(item) for item in subscriptions if item.get("id")}
    if not mapping:
        return False

    await _redis_client.delete("tg_subscriptions")
    await _redis_client.hset("tg_subscriptions", mapping=mapping)
    log.info("Saved %s telegram subscriptions to Redis", len(mapping))
    return True


async def load_push_subscriptions_raw() -> list[str]:
    if not _redis_client:
        return []

    subs = await _redis_client.lrange("subscriptions", 0, -1)
    return [item.decode() if isinstance(item, (bytes, bytearray)) else item for item in subs]


async def load_tg_subscriptions_raw() -> list[str]:
    if not _redis_client:
        return []

    subs = await _redis_client.hvals("tg_subscriptions")
    return [item.decode() if isinstance(item, (bytes, bytearray)) else item for item in subs]


async def load_all_into_subcription() -> bool:
    """
    Load push and Telegram subscriptions from Redis straight into the in-memory
    caches maintained by untils.subcription.
    """
    if not _redis_client:
        return False

    from untils import subcription

    push_raw = await load_push_subscriptions_raw()
    tg_raw = await load_tg_subscriptions_raw()

    subcription.replace_push_subscriptions(push_raw)
    subcription.replace_telegram_subscriptions(tg_raw)

    log.info("Loaded subscriptions from Redis: push=%s, tg=%s", len(push_raw), len(tg_raw))

    return True
