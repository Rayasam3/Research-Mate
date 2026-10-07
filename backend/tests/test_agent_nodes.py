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


@pytest.fixture(autouse=True)
def _fake_embeddings(monkeypatch):
    """Ranking tests must not load the real embedding model."""
    from app.services import domain

    monkeypatch.setattr(domain, "_embed", lambda texts: [[1.0, 0.0] for _ in texts])


@pytest.mark.asyncio
async def test_domain_node_votes_on_field():
    papers = [_paper(external_id="1", field="Computer Science"),
              _paper(external_id="2", field="Computer Science"),
              _paper(external_id="3", field="Medicine & Health")]
    result = await nodes.domain_node({"topic": "gnn", "candidate_papers": papers})
    assert result["detected_field"] == "Computer Science"
    assert result["field_counts"]["Computer Science"] == 2


@pytest.mark.asyncio
async def test_filter_node_prefers_papers_with_pdf():
    with_pdf = _paper(external_id="has_pdf", pdf_url="https://example.com/a.pdf")
    without_pdf = _paper(external_id="no_pdf", pdf_url=None)

    state = {"topic": "test", "candidate_papers": [without_pdf, with_pdf], "max_papers": 1}
    result = await nodes.filter_node(state)

    assert len(result["selected_papers"]) == 1
    assert result["selected_papers"][0].external_id == "has_pdf"


@pytest.mark.asyncio
async def test_filter_node_respects_max_papers():
    papers = [_paper(external_id=str(i)) for i in range(5)]
    result = await nodes.filter_node({"topic": "test", "candidate_papers": papers, "max_papers": 2})
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
    assert result["selected_papers"] == []
    assert "download exploded" in result["skipped_papers"][0]["reason"]


@pytest.mark.asyncio
async def test_summarize_node_only_summarizes_successful_ingests(monkeypatch):
    call_log = []

    async def fake_summarize(paper_id, force=False, user_id=None):
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


@pytest.mark.asyncio
async def test_ingest_node_replaces_unreadable_paper_with_spare(monkeypatch):
    bad = _paper(external_id="bad", title="Bad")
    good_1 = _paper(external_id="g1", title="Good 1")
    good_2 = _paper(external_id="g2", title="Good 2")

    async def fake_ingest(paper, force=False):
        pid = nodes.make_paper_id(paper)
        if paper.external_id == "bad":
            return {"paper_id": pid, "status": "download_failed", "message": "not a PDF"}
        return {"paper_id": pid, "status": "success", "chunk_count": 5}

    monkeypatch.setattr(nodes, "ingest_paper", fake_ingest)

    state = {"max_papers": 2, "selected_papers": [bad, good_1], "reserve_papers": [good_2]}
    result = await nodes.ingest_node(state)

    assert [p.external_id for p in result["selected_papers"]] == ["g1", "g2"]
    assert result["skipped_papers"] == [{"title": "Bad", "reason": "not a PDF"}]
    assert result["reserve_papers"] == []


@pytest.mark.asyncio
async def test_ingest_node_stops_when_enough_papers_are_readable(monkeypatch):
    papers = [_paper(external_id=str(i)) for i in range(4)]
    tried = []

    async def fake_ingest(paper, force=False):
        tried.append(paper.external_id)
        return {"paper_id": nodes.make_paper_id(paper), "status": "success"}

    monkeypatch.setattr(nodes, "ingest_paper", fake_ingest)

    result = await nodes.ingest_node({"max_papers": 2, "selected_papers": papers[:2], "reserve_papers": papers[2:]})
    assert tried == ["0", "1"]
    assert len(result["reserve_papers"]) == 2        # spares were never touched


@pytest.mark.asyncio
async def test_ingest_node_gives_fewer_papers_when_not_enough_are_readable(monkeypatch):
    papers = [_paper(external_id=str(i)) for i in range(3)]

    async def fake_ingest(paper, force=False):
        return {"paper_id": nodes.make_paper_id(paper), "status": "no_pdf_available", "message": "no pdf"}

    monkeypatch.setattr(nodes, "ingest_paper", fake_ingest)

    result = await nodes.ingest_node({"max_papers": 3, "selected_papers": papers})
    assert result["selected_papers"] == []
    assert len(result["skipped_papers"]) == 3


@pytest.mark.asyncio
async def test_summarize_node_tops_up_from_spares_when_a_summary_fails(monkeypatch):
    first = _paper(external_id="first", title="First")
    spare = _paper(external_id="spare", title="Spare")
    first_id, spare_id = nodes.make_paper_id(first), nodes.make_paper_id(spare)

    async def fake_summarize(paper_id, force=False, user_id=None):
        if paper_id == first_id:
            return {"paper_id": paper_id, "status": "llm_failed", "card": None, "message": "timeout"}
        return {"paper_id": paper_id, "status": "success", "card": {}}

    async def fake_ingest(paper, force=False):
        return {"paper_id": nodes.make_paper_id(paper), "status": "success"}

    monkeypatch.setattr(nodes, "summarize_paper", fake_summarize)
    monkeypatch.setattr(nodes, "ingest_paper", fake_ingest)

    state = {
        "max_papers": 1,
        "selected_papers": [first],
        "reserve_papers": [spare],
        "ingest_results": {first_id: {"status": "success"}},
    }
    result = await nodes.summarize_node(state)

    assert list(result["summary_results"]) == [spare_id]
    assert [p.external_id for p in result["selected_papers"]] == ["spare"]
    assert result["skipped_papers"] == [{"title": "First", "reason": "timeout"}]
