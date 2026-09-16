from datetime import date

import pytest

from app.schemas.paper import Paper, PaperSource
from agents import nodes


def _paper(**overrides) -> Paper:
    defaults = dict(
        external_id="1",
        source=PaperSource.ARXIV,
        title="Test Paper",
        authors=["A. Author"],
        abstract="An abstract.",
        published_date=date(2022, 1, 1),
        pdf_url="https://arxiv.org/pdf/1234.5678",
        doi=None,
        url="https://arxiv.org/abs/1234.5678",
    )
    defaults.update(overrides)
    return Paper(**defaults)


@pytest.mark.asyncio
async def test_search_node_success(monkeypatch):
    papers = [_paper(external_id="a"), _paper(external_id="b")]

    async def fake_search(**kwargs):
        return papers

    monkeypatch.setattr(nodes, "search_all_sources", fake_search)

    result = await nodes.search_node({"topic": "test", "max_papers": 5})
    assert result["candidate_papers"] == papers


@pytest.mark.asyncio
async def test_search_node_failure_recorded_as_error(monkeypatch):
    async def fake_search(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(nodes, "search_all_sources", fake_search)

    result = await nodes.search_node({"topic": "test", "max_papers": 5, "errors": []})
    assert result["candidate_papers"] == []
    assert "Search failed" in result["errors"][0]


@pytest.mark.asyncio
async def test_filter_node_prefers_papers_with_pdf():
    with_pdf = _paper(external_id="has_pdf", pdf_url="https://example.com/a.pdf")
    without_pdf = _paper(external_id="no_pdf", pdf_url=None)

    state = {"candidate_papers": [without_pdf, with_pdf], "max_papers": 1}
    result = await nodes.filter_node(state)

    assert len(result["selected_papers"]) == 1
    assert result["selected_papers"][0].external_id == "has_pdf"


@pytest.mark.asyncio
async def test_filter_node_respects_max_papers():
    papers = [_paper(external_id=str(i)) for i in range(5)]
    result = await nodes.filter_node({"candidate_papers": papers, "max_papers": 2})
    assert len(result["selected_papers"]) == 2


@pytest.mark.asyncio
async def test_ingest_node_processes_all_selected_papers(monkeypatch):
    paper_a = _paper(external_id="a")
    paper_b = _paper(external_id="b")

    async def fake_ingest(paper, force=False):
        return {"paper_id": nodes.make_paper_id(paper), "status": "success", "chunk_count": 10}

    monkeypatch.setattr(nodes, "ingest_paper", fake_ingest)

    state = {"selected_papers": [paper_a, paper_b], "errors": []}
    result = await nodes.ingest_node(state)

    assert len(result["ingest_results"]) == 2
    assert all(r["status"] == "success" for r in result["ingest_results"].values())


@pytest.mark.asyncio
async def test_ingest_node_records_failure_without_crashing(monkeypatch):
    paper_a = _paper(external_id="a")

    async def fake_ingest(paper, force=False):
        raise RuntimeError("download exploded")

    monkeypatch.setattr(nodes, "ingest_paper", fake_ingest)

    state = {"selected_papers": [paper_a], "errors": []}
    result = await nodes.ingest_node(state)

    assert result["ingest_results"] == {}
    assert "Ingest failed" in result["errors"][0]


@pytest.mark.asyncio
async def test_summarize_node_only_summarizes_successful_ingests(monkeypatch):
    call_log = []

    async def fake_summarize(paper_id, force=False):
        call_log.append(paper_id)
        return {"paper_id": paper_id, "status": "success", "card": {}}

    monkeypatch.setattr(nodes, "summarize_paper", fake_summarize)

    state = {
        "ingest_results": {
            "good_paper": {"status": "success"},
            "bad_paper": {"status": "download_failed"},
        },
        "errors": [],
    }
    result = await nodes.summarize_node(state)

    assert call_log == ["good_paper"]
    assert "good_paper" in result["summary_results"]
    assert "bad_paper" not in result["summary_results"]