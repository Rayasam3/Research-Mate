"""
A simple file-based cache for search results, keyed by the exact query
parameters. This exists mainly to avoid re-hitting ArXiv/Semantic
Scholar's tight rate limits while developing/testing (repeating the same
search costs nothing once cached), and it also speeds up popular topics
once this is a live public service. Redis will replace this in Phase 8
for multi-instance deployments; a local JSON file is enough for now.
"""
import hashlib
import json
import logging
import time
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def _cache_dir() -> Path:
    path = Path(settings.cache_dir) / "search"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_key(topic: str, sources: list[str], max_results: int, year_from, year_to) -> str:
    raw = f"{topic.lower().strip()}|{sorted(sources)}|{max_results}|{year_from}|{year_to}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached_search(topic: str, sources: list[str], max_results: int, year_from, year_to) -> list[dict] | None:
    key = _cache_key(topic, sources, max_results, year_from, year_to)
    path = _cache_dir() / f"{key}.json"
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupt search cache file %s, ignoring", path)
        return None

    age_seconds = time.time() - payload.get("cached_at", 0)
    if age_seconds > settings.search_cache_ttl_seconds:
        return None  # expired

    logger.info("Search cache hit for topic=%r (age=%.0fs)", topic, age_seconds)
    return payload.get("results")


def set_cached_search(
    topic: str, sources: list[str], max_results: int, year_from, year_to, results: list[dict]
) -> None:
    key = _cache_key(topic, sources, max_results, year_from, year_to)
    path = _cache_dir() / f"{key}.json"
    try:
        path.write_text(json.dumps({"cached_at": time.time(), "results": results}), encoding="utf-8")
    except OSError:
        logger.warning("Failed to write search cache file %s", path)