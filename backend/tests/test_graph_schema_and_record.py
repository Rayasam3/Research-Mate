from datetime import date
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.paper_record import MethodMention, PaperRecord, ResultItem
from app.services import graph_ingestion
from app.services.graph_schema import normalize_key, statement_key


def _fake_paper():
    return SimpleNamespace(
        title="T",
        authors=["A B", "C D"],
        published_date=date(2023, 1, 1),
        source=SimpleNamespace(value="arxiv"),
    )


def test_normalize_key_merges_variants():
    assert normalize_key("Graph Neural Network (GNN)") == "graph neural network"
    assert normalize_key("GNN") == "graph neural network"
    assert normalize_key("  Graph   Neural Networks ") == "graph neural network"


def test_normalize_key_keeps_distinct_names_distinct():
    assert normalize_key("Graph Attention Network") != normalize_key("Graph Neural Network")


def test_normalize_key_empty():
    assert normalize_key("") == ""
    assert normalize_key(None) == ""


def test_statement_key_stable_per_paper():
    assert statement_key("p1", "Needs Data") == statement_key("p1", "  needs data ")
    assert statement_key("p1", "x") != statement_key("p2", "x")


def test_record_defaults_and_validation():
    record = PaperRecord()
    assert record.methods == [] and record.datasets == []
    assert MethodMention(name="x").role == "used"
    with pytest.raises(ValidationError):
        MethodMention(name="x", role="invented")


@pytest.mark.asyncio
async def test_index_record_writes_expected_structure(monkeypatch):
    calls = []

    async def fake_run_query(query, params=None):
        calls.append((query, params or {}))
        return []

    monkeypatch.setattr(graph_ingestion, "run_query", fake_run_query)

    record = PaperRecord(
        domain="Computer Vision",
        task="image classification",
        methods=[MethodMention(name="Vision Transformer (ViT)", role="proposed", novelty="pure attention")],
        datasets=["ImageNet"],
        results=[ResultItem(method="ViT", dataset="CIFAR-100", metric="accuracy", value="91.2")],
        limitations=["Needs large pretraining data"],
        future_work=["Apply to video"],
    )
    counts = await graph_ingestion.index_record_in_graph("arxiv_1", _fake_paper(), record, "user_1")

    assert calls[0][1]["user_id"] == "user_1"
    # "Vision Transformer (ViT)" and "ViT" must merge into one method node
    assert counts["methods"] == 1
    # ImageNet + CIFAR-100 (implied by the result)
    assert counts["datasets"] == 2
    assert counts["results"] == 1
    assert counts["limitations"] == 1 and counts["future_work"] == 1
    method_params = next(p for _, p in calls if "methods" in p)
    assert method_params["methods"][0]["role"] == "proposed"


@pytest.mark.asyncio
async def test_legacy_wrapper_still_works(monkeypatch):
    async def fake_run_query(query, params=None):
        return []

    monkeypatch.setattr(graph_ingestion, "run_query", fake_run_query)
    counts = await graph_ingestion.index_paper_in_graph(
        "arxiv_1", _fake_paper(), ["self-attention"], ["WMT 2014"], "user_1"
    )
    assert counts["methods"] == 1 and counts["datasets"] == 1 and counts["results"] == 0