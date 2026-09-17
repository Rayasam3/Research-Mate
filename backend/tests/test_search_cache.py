import pytest

from app.core.config import settings
from app.services import search_cache


@pytest.fixture(autouse=True)
def _disable_redis(monkeypatch):
    """
    Tests run with Redis disabled by default, so they test the graceful
    fallback path (no caching, no crash) without needing a real Redis
    connection - fast, isolated, no external dependency.
    """
    monkeypatch.setattr(settings, "use_redis_cache", False)
    yield


@pytest.mark.asyncio
async def test_get_cached_search_returns_none_when_disabled():
    result = await search_cache.get_cached_search("topic", ["arxiv"], 5, None, None)
    assert result is None


@pytest.mark.asyncio
async def test_set_cached_search_no_ops_when_disabled():
    # Should not raise even though nothing is actually cached.
    await search_cache.set_cached_search("topic", ["arxiv"], 5, None, None, [{"a": 1}])


@pytest.mark.asyncio
async def test_get_cached_search_falls_back_gracefully_when_redis_unreachable(monkeypatch):
    monkeypatch.setattr(settings, "use_redis_cache", True)

    async def fake_unavailable():
        return False

    monkeypatch.setattr(search_cache, "redis_is_available", fake_unavailable)

    result = await search_cache.get_cached_search("topic", ["arxiv"], 5, None, None)
    assert result is None


@pytest.mark.asyncio
async def test_set_and_get_cached_search_roundtrip_with_fake_redis(monkeypatch):
    monkeypatch.setattr(settings, "use_redis_cache", True)

    store = {}

    class FakeRedisClient:
        async def get(self, key):
            return store.get(key)

        async def set(self, key, value, ex=None):
            store[key] = value

    async def fake_available():
        return True

    monkeypatch.setattr(search_cache, "redis_is_available", fake_available)
    monkeypatch.setattr(search_cache, "get_redis_client", lambda: FakeRedisClient())

    results = [{"title": "Test Paper"}]
    await search_cache.set_cached_search("topic", ["arxiv"], 5, None, None, results)
    cached = await search_cache.get_cached_search("topic", ["arxiv"], 5, None, None)
    assert cached == results


@pytest.mark.asyncio
async def test_cache_key_is_case_insensitive_on_topic(monkeypatch):
    monkeypatch.setattr(settings, "use_redis_cache", True)

    store = {}

    class FakeRedisClient:
        async def get(self, key):
            return store.get(key)

        async def set(self, key, value, ex=None):
            store[key] = value

    async def fake_available():
        return True

    monkeypatch.setattr(search_cache, "redis_is_available", fake_available)
    monkeypatch.setattr(search_cache, "get_redis_client", lambda: FakeRedisClient())

    await search_cache.set_cached_search("Transformers", ["arxiv"], 5, None, None, [{"a": 1}])
    cached = await search_cache.get_cached_search("transformers", ["arxiv"], 5, None, None)
    assert cached == [{"a": 1}]