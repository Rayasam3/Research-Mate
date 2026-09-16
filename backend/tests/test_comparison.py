import pytest

from app.services import comparison


@pytest.mark.asyncio
async def test_get_comparison_table_empty_list_returns_empty():
    result = await comparison.get_comparison_table([])
    assert result == []


@pytest.mark.asyncio
async def test_get_comparison_table_cleans_null_collections(monkeypatch):
    async def fake_run_query(query, params=None):
        return [
            {
                "paper_id": "arxiv_123",
                "title": "Some Paper",
                "year": 2022,
                "methods": [None],
                "datasets": ["ImageNet", None],
            }
        ]

    monkeypatch.setattr(comparison, "run_query", fake_run_query)

    result = await comparison.get_comparison_table(["arxiv_123"])
    assert result[0]["methods"] == []
    assert result[0]["datasets"] == ["ImageNet"]


@pytest.mark.asyncio
async def test_find_related_papers_uses_correct_relationship(monkeypatch):
    captured_query = {}

    async def fake_run_query(query, params=None):
        captured_query["query"] = query
        captured_query["params"] = params
        return [{"paper_id": "p1", "title": "Related Paper", "year": 2021}]

    monkeypatch.setattr(comparison, "run_query", fake_run_query)

    result = await comparison.find_related_papers("dataset", "ImageNet", exclude_paper_id="p0")
    assert "EVALUATED_ON" in captured_query["query"]
    assert captured_query["params"]["entity_name"] == "ImageNet"
    assert result[0]["paper_id"] == "p1"


@pytest.mark.asyncio
async def test_find_related_papers_method_type_uses_method_relationship(monkeypatch):
    captured_query = {}

    async def fake_run_query(query, params=None):
        captured_query["query"] = query
        return []

    monkeypatch.setattr(comparison, "run_query", fake_run_query)

    await comparison.find_related_papers("method", "self-attention")
    assert "USES_METHOD" in captured_query["query"]