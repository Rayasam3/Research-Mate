import time

import pytest

from app.core.config import settings
from app.services import search_cache


@pytest.fixture(autouse=True)
def _use_tmp_cache_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    yield


def test_cache_miss_returns_none():
    result = search_cache.get_cached_search("nonexistent topic", ["arxiv"], 5, None, None)
    assert result is None


def test_cache_set_then_get_returns_same_results():
    results = [{"title": "Attention Is All You Need", "external_id": "1706.03762"}]
    search_cache.set_cached_search("transformers", ["arxiv"], 5, None, None, results)

    cached = search_cache.get_cached_search("transformers", ["arxiv"], 5, None, None)
    assert cached == results


def test_cache_key_is_case_insensitive_on_topic():
    results = [{"title": "Test Paper"}]
    search_cache.set_cached_search("Transformers", ["arxiv"], 5, None, None, results)

    cached = search_cache.get_cached_search("transformers", ["arxiv"], 5, None, None)
    assert cached == results


def test_cache_different_params_are_separate_entries():
    search_cache.set_cached_search("topic", ["arxiv"], 5, None, None, [{"a": 1}])
    search_cache.set_cached_search("topic", ["pubmed"], 5, None, None, [{"a": 2}])

    assert search_cache.get_cached_search("topic", ["arxiv"], 5, None, None) == [{"a": 1}]
    assert search_cache.get_cached_search("topic", ["pubmed"], 5, None, None) == [{"a": 2}]


def test_cache_expired_entry_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "search_cache_ttl_seconds", 1)
    search_cache.set_cached_search("topic", ["arxiv"], 5, None, None, [{"a": 1}])
    time.sleep(1.1)
    assert search_cache.get_cached_search("topic", ["arxiv"], 5, None, None) is None