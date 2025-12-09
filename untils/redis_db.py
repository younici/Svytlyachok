import redis.asyncio as redis

import os
from dotenv import load_dotenv

load_dotenv()

import logging

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

async def get_redis_client() -> redis.Redis:
    return _redis_client

async def load_subscriptions():
    if not _redis_client:
        return

    subs = await _redis_client.lrange("subscriptions", 0, -1)
    subs = [item.decode() if isinstance(item, (bytes, bytearray)) else item for item in subs]
    log.info(f"Redis subscriptions loaded: {len(subs)}")
    return subs
