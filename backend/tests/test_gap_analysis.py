import pytest

from app.services import gap_analysis
from app.services.gap_analysis import _find_isolated_items, analyze_gaps
from app.services.llm_client import LlmError


def test_find_isolated_items_single_occurrence():
    rows = [
        {"methods": ["A", "B"]},
        {"methods": ["B", "C"]},
    ]
    result = _find_isolated_items(rows, "methods")
    assert result == ["A", "C"]


def test_find_isolated_items_no_isolated():
    rows = [
        {"methods": ["A", "B"]},
        {"methods": ["A", "B"]},
    ]
    result = _find_isolated_items(rows, "methods")
    assert result == []


def test_find_isolated_items_empty_rows():
    assert _find_isolated_items([], "methods") == []


@pytest.mark.asyncio
async def test_analyze_gaps_no_isolated_items_skips_llm(monkeypatch):
    async def fake_get_comparison_table(paper_ids):
        return [{"methods": ["A"], "datasets": ["X"]}, {"methods": ["A"], "datasets": ["X"]}]

    async def fail_if_called(prompt):
        raise AssertionError("LLM should not be called when there are no isolated items")

    monkeypatch.setattr(gap_analysis, "get_comparison_table", fake_get_comparison_table)
    monkeypatch.setattr(gap_analysis, "generate_json", fail_if_called)

    result = await analyze_gaps(["p1", "p2"])
    assert result["isolated_methods"] == []
    assert result["method_gaps"] == []


@pytest.mark.asyncio
async def test_analyze_gaps_success(monkeypatch):
    async def fake_get_comparison_table(paper_ids):
        return [{"methods": ["A", "B"], "datasets": []}, {"methods": ["A"], "datasets": []}]

    async def fake_generate_json(prompt):
        return {"method_gaps": ["Method B has only been used in one paper."], "dataset_gaps": []}

    monkeypatch.setattr(gap_analysis, "get_comparison_table", fake_get_comparison_table)
    monkeypatch.setattr(gap_analysis, "generate_json", fake_generate_json)

    result = await analyze_gaps(["p1", "p2"])
    assert result["isolated_methods"] == ["B"]
    assert result["method_gaps"] == ["Method B has only been used in one paper."]


@pytest.mark.asyncio
async def test_analyze_gaps_llm_failure_returns_facts_without_phrasing(monkeypatch):
    async def fake_get_comparison_table(paper_ids):
        return [{"methods": ["A", "B"], "datasets": []}, {"methods": ["A"], "datasets": []}]

    async def fake_generate_json(prompt):
        raise LlmError("boom")

    monkeypatch.setattr(gap_analysis, "get_comparison_table", fake_get_comparison_table)
    monkeypatch.setattr(gap_analysis, "generate_json", fake_generate_json)

    result = await analyze_gaps(["p1", "p2"])
    assert result["isolated_methods"] == ["B"]
    assert result["method_gaps"] == []