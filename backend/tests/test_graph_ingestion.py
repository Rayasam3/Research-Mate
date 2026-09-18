from datetime import date

import pytest

from app.schemas.paper import Paper, PaperSource
from app.services import graph_ingestion


def _paper(**overrides) -> Paper:
    defaults = dict(
        external_id="1706.03762",
        source=PaperSource.ARXIV,
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer"],
        abstract="A transformer paper.",
        published_date=date(2017, 6, 12),
        pdf_url="https://arxiv.org/pdf/1706.03762",
        doi=None,
        url="https://arxiv.org/abs/1706.03762",
    )
    defaults.update(overrides)
    return Paper(**defaults)


@pytest.mark.asyncio
async def test_index_paper_in_graph_runs_expected_queries(monkeypatch):
    queries_run = []

    async def fake_run_query(query, params=None):
        queries_run.append((query, params))
        return []

    monkeypatch.setattr(graph_ingestion, "run_query", fake_run_query)

    result = await graph_ingestion.index_paper_in_graph(
        "arxiv_1706.03762", _paper(), methods=["self-attention"], datasets=["WMT 2014"], user_id="user_123"
    )

    assert result["paper_id"] == "arxiv_1706.03762"
    assert result["methods"] == ["self-attention"]
    assert result["datasets"] == ["WMT 2014"]

    # 1 paper MERGE + 2 author MERGEs + 1 method MERGE + 1 dataset MERGE = 5 queries
    assert len(queries_run) == 5


@pytest.mark.asyncio
async def test_index_paper_in_graph_handles_no_methods_or_datasets(monkeypatch):
    queries_run = []

    async def fake_run_query(query, params=None):
        queries_run.append((query, params))
        return []

    monkeypatch.setattr(graph_ingestion, "run_query", fake_run_query)

    paper = _paper(authors=[])
    await graph_ingestion.index_paper_in_graph(
        "arxiv_1706.03762", paper, methods=[], datasets=[], user_id="user_123"
    )

    # Just the 1 paper MERGE query, no author/method/dataset queries
    assert len(queries_run) == 1