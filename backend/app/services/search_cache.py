"""
Caches search results, keyed by the exact query parameters. Backed by
Redis (Phase 8) when available and enabled, since a shared cache is
required once the app runs across multiple processes/instances; falls
back to no caching (not a crash) if Redis is unreachable, since a slower
search is far better than a broken one.
"""
import hashlib
import json
import logging

from app.core.config import settings
from app.services.redis_client import get_redis_client, redis_is_available

logger = logging.getLogger(__name__)


def _cache_key(topic: str, sources: list[str], max_results: int, year_from, year_to) -> str:
    raw = f"{topic.lower().strip()}|{sorted(sources)}|{max_results}|{year_from}|{year_to}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"research_mate:search:{digest}"


async def get_cached_search(topic: str, sources: list[str], max_results: int, year_from, year_to) -> list[dict] | None:
    if not settings.use_redis_cache:
        return None
    if not await redis_is_available():
        return None

    key = _cache_key(topic, sources, max_results, year_from, year_to)
    try:
        client = get_redis_client()
        raw = await client.get(key)
        if raw is None:
            return None
        logger.info("Redis search cache hit for topic=%r", topic)
        return json.loads(raw)
    except Exception:
        logger.exception("Redis read failed for search cache key=%s", key)
        return None


async def set_cached_search(
    topic: str, sources: list[str], max_results: int, year_from, year_to, results: list[dict]
) -> None:
    if not settings.use_redis_cache:
        return
    if not await redis_is_available():
        return

    key = _cache_key(topic, sources, max_results, year_from, year_to)
    try:
        client = get_redis_client()
        await client.set(key, json.dumps(results), ex=settings.search_cache_ttl_seconds)
    except Exception:
        logger.exception("Redis write failed for search cache key=%s", key)