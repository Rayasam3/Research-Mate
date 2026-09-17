from datetime import date

import pytest

from app.schemas.paper import Paper, PaperSource
from app.services import search_service


def _paper(**overrides) -> Paper:
    defaults = dict(
        external_id="1",
        source=PaperSource.ARXIV,
        title="Attention Is All You Need",
        authors=["A. Vaswani"],
        abstract="A transformer paper.",
        published_date=date(2017, 6, 12),
        pdf_url="https://arxiv.org/pdf/1706.03762",
        doi=None,
        url="https://arxiv.org/abs/1706.03762",
    )
    defaults.update(overrides)
    return Paper(**defaults)


@pytest.fixture(autouse=True)
def _disable_search_cache(monkeypatch):
    # Disable the Redis-backed search cache for these tests, so they
    # never get a false "cache hit" from previous test runs and don't
    # need a real Redis connection.
    from app.core.config import settings

    monkeypatch.setattr(settings, "use_redis_cache", False)
    yield


def test_dedupe_by_doi():
    a = _paper(external_id="a", doi="10.1000/xyz")
    b = _paper(external_id="b", source=PaperSource.SEMANTIC_SCHOLAR, doi="10.1000/xyz")
    deduped = search_service._dedupe([a, b])
    assert len(deduped) == 1


def test_dedupe_by_normalized_title_when_no_doi():
    a = _paper(external_id="a", title="Attention Is All You Need", doi=None)
    b = _paper(
        external_id="b",
        source=PaperSource.PUBMED,
        title="attention is all you need!!",
        doi=None,
    )
    deduped = search_service._dedupe([a, b])
    assert len(deduped) == 1


def test_no_dedupe_for_distinct_papers():
    a = _paper(external_id="a", title="Paper One", doi="10.1/one")
    b = _paper(external_id="b", title="Paper Two", doi="10.1/two")
    deduped = search_service._dedupe([a, b])
    assert len(deduped) == 2


def test_filter_by_year_excludes_out_of_range():
    old = _paper(external_id="old", published_date=date(2010, 1, 1))
    new = _paper(external_id="new", published_date=date(2023, 1, 1))
    filtered = search_service._filter_by_year([old, new], year_from=2020, year_to=None)
    assert [p.external_id for p in filtered] == ["new"]


def test_filter_by_year_excludes_undated_papers_when_range_given():
    undated = _paper(external_id="undated", published_date=None)
    filtered = search_service._filter_by_year([undated], year_from=2020, year_to=None)
    assert filtered == []


def test_filter_by_year_no_range_returns_all():
    a = _paper(external_id="a", published_date=None)
    b = _paper(external_id="b", published_date=date(2020, 1, 1))
    filtered = search_service._filter_by_year([a, b], year_from=None, year_to=None)
    assert len(filtered) == 2


@pytest.mark.asyncio
async def test_search_all_sources_merges_and_sorts(monkeypatch):
    older = _paper(external_id="old", title="Older Paper", published_date=date(2015, 1, 1), doi="10.1/old")
    newer = _paper(external_id="new", title="Newer Paper", published_date=date(2023, 1, 1), doi="10.1/new")

    async def fake_arxiv(topic, max_results):
        return [older]

    async def fake_semantic_scholar(topic, max_results):
        return [newer]

    async def fake_pubmed(topic, max_results):
        return []

    async def fake_openalex(topic, max_results):
        return []

    monkeypatch.setitem(search_service._SOURCE_FUNCS, PaperSource.ARXIV, fake_arxiv)
    monkeypatch.setitem(search_service._SOURCE_FUNCS, PaperSource.SEMANTIC_SCHOLAR, fake_semantic_scholar)
    monkeypatch.setitem(search_service._SOURCE_FUNCS, PaperSource.PUBMED, fake_pubmed)
    monkeypatch.setitem(search_service._SOURCE_FUNCS, PaperSource.OPENALEX, fake_openalex)

    results = await search_service.search_all_sources("transformers")
    assert [p.external_id for p in results] == ["new", "old"]

