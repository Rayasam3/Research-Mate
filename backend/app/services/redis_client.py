"""
Thin wrapper around a Redis connection, used as a module-level singleton.
Redis replaces the Phase 1 file-based search cache here in Phase 8 - same
purpose (avoid re-hitting rate-limited external APIs, speed up repeated
topics), but works correctly across multiple backend processes/instances,
which a local JSON file cannot.
"""
import logging

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def redis_is_available() -> bool:
    """
    Checks whether Redis is actually reachable right now. Used so the
    search cache can gracefully fall back to "no cache" instead of
    crashing the whole search if Redis is down.
    """
    try:
        client = get_redis_client()
        await client.ping()
        return True
    except Exception:
        logger.warning("Redis is not reachable; falling back to no caching for this request")
        return False