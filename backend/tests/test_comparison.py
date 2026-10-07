import pytest

from app.services import comparison


@pytest.mark.asyncio
async def test_get_comparison_table_empty_list_returns_empty():
    assert await comparison.get_comparison_table([], "user1") == []


@pytest.mark.asyncio
async def test_comparison_marks_shared_and_unique_methods(monkeypatch):
    async def fake_run_query(query, params=None):
        assert params["user_id"] == "user1"
        return [
            {"paper_id": "p1", "title": "A", "year": 2023, "citations": 5, "domain": "Computer Science",
             "task": "node classification", "datasets": ["Cora", None], "n_limitations": 2, "n_future_work": 1,
             "methods": [{"key": "gcn", "name": "GCN", "role": "baseline", "novelty": None},
                         {"key": "newnet", "name": "NewNet", "role": "proposed", "novelty": "adds X"},
                         {"key": None, "name": None, "role": None, "novelty": None}]},
            {"paper_id": "p2", "title": "B", "year": 2024, "citations": None, "domain": None,
             "task": None, "datasets": [], "n_limitations": 0, "n_future_work": 0,
             "methods": [{"key": "gcn", "name": "GCN", "role": "baseline", "novelty": None}]},
        ]

    monkeypatch.setattr(comparison, "run_query", fake_run_query)
    rows = await comparison.get_comparison_table(["p1", "p2"], "user1")

    assert rows[0]["datasets"] == ["Cora"]                       # None cleaned out
    assert rows[0]["unique_methods"] == ["NewNet"]               # what makes paper 1 different
    assert [m["shared"] for m in rows[0]["methods"]] == [True, False]
    assert rows[1]["unique_methods"] == []


@pytest.mark.asyncio
async def test_find_related_papers_uses_normalized_key(monkeypatch):
    seen = {}

    async def fake_run_query(query, params=None):
        seen["query"], seen["params"] = query, params
        return []

    monkeypatch.setattr(comparison, "run_query", fake_run_query)
    await comparison.find_related_papers("method", "GNNs", "user1", "p9")
    assert "USES_METHOD" in seen["query"]
    assert seen["params"]["key"] == "graph neural network"       # alias-normalized
    assert seen["params"]["user_id"] == "user1"


@pytest.mark.asyncio
async def test_find_related_papers_dataset_uses_evaluated_on(monkeypatch):
    seen = {}

    async def fake_run_query(query, params=None):
        seen["query"] = query
        return []

    monkeypatch.setattr(comparison, "run_query", fake_run_query)
    await comparison.find_related_papers("dataset", "ImageNet", "user1")
    assert "EVALUATED_ON" in seen["query"]
