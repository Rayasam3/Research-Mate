from datetime import date
from types import SimpleNamespace

import pytest

from app.services import graph_ingestion


def _paper(authors=None):
    return SimpleNamespace(
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer"] if authors is None else authors,
        published_date=date(2017, 6, 12),
        source=SimpleNamespace(value="arxiv"),
    )


@pytest.mark.asyncio
async def test_index_paper_in_graph_runs_expected_queries(monkeypatch):
    calls = []

    async def fake_run_query(query, params=None):
        calls.append((query, params or {}))
        return []

    monkeypatch.setattr(graph_ingestion, "run_query", fake_run_query)

    result = await graph_ingestion.index_paper_in_graph(
        "arxiv_1706.03762", _paper(), methods=["self-attention"], datasets=["WMT 2014"], user_id="user_123"
    )

    # Paper node, authors, methods, datasets: one batched query each.
    assert len(calls) == 4
    assert calls[0][1]["paper_id"] == "arxiv_1706.03762"
    assert calls[0][1]["user_id"] == "user_123"
    assert calls[1][1]["authors"] == ["Ashish Vaswani", "Noam Shazeer"]
    assert calls[2][1]["methods"][0]["key"] == "self-attention"
    assert calls[3][1]["datasets"][0]["key"] == "wmt 2014"
    assert result["authors"] == 2 and result["methods"] == 1 and result["datasets"] == 1


@pytest.mark.asyncio
async def test_index_paper_in_graph_handles_no_methods_or_datasets(monkeypatch):
    calls = []

    async def fake_run_query(query, params=None):
        calls.append((query, params or {}))
        return []

    monkeypatch.setattr(graph_ingestion, "run_query", fake_run_query)

    result = await graph_ingestion.index_paper_in_graph(
        "arxiv_1706.03762", _paper(authors=[]), methods=[], datasets=[], user_id="user_123"
    )

    # Only the Paper node is written; nothing else to batch.
    assert len(calls) == 1
    assert result["authors"] == 0 and result["methods"] == 0 and result["datasets"] == 0