import pytest

from app.services import graph_view


@pytest.mark.asyncio
async def test_graph_view_builds_nodes_and_links(monkeypatch):
    async def fake_run_query(query, params=None):
        if "RETURN p.paper_id AS id" in query:
            return [{"id": "p1", "name": "Paper 1", "year": 2024}]
        if "USES_METHOD" in query:
            return [{"source": "p1", "key": "gcn", "name": "GCN", "role": "proposed"}]
        if "EVALUATED_ON" in query:
            return [{"source": "p1", "key": "cora", "name": "Cora", "role": None}]
        if "TESTED_ON" in query:
            return [{"m": "gcn", "d": "cora", "metric": "acc", "value": "81"}]
        if "Gap" in query:
            return []
        return []

    monkeypatch.setattr(graph_view, "run_query", fake_run_query)
    view = await graph_view.get_graph_view(["p1"], "user1")

    ids = {n["id"] for n in view["nodes"]}
    assert {"p1", "Method:gcn", "Dataset:cora"} <= ids
    types = {(l["type"]) for l in view["links"]}
    assert {"USES_METHOD", "EVALUATED_ON", "TESTED_ON"} <= types


@pytest.mark.asyncio
async def test_graph_view_empty_when_no_papers(monkeypatch):
    async def fake_run_query(query, params=None):
        return []

    monkeypatch.setattr(graph_view, "run_query", fake_run_query)
    assert await graph_view.get_graph_view(["nope"], "user1") == {"nodes": [], "links": []}


@pytest.mark.asyncio
async def test_method_role_proposed_wins_over_baseline(monkeypatch):
    async def fake_run_query(query, params=None):
        if "RETURN p.paper_id AS id" in query:
            return [{"id": "p1", "name": "P1", "year": 2024}, {"id": "p2", "name": "P2", "year": 2024}]
        if "USES_METHOD" in query:
            return [
                {"source": "p1", "key": "gcn", "name": "GCN", "role": "baseline"},
                {"source": "p2", "key": "gcn", "name": "GCN", "role": "proposed"},
                {"source": "p2", "key": "gat", "name": "GAT", "role": "baseline"},
                {"source": "p1", "key": "mlp", "name": "MLP", "role": None},
            ]
        return []

    monkeypatch.setattr(graph_view, "run_query", fake_run_query)
    view = await graph_view.get_graph_view(["p1", "p2"], "user1")
    roles = {n["id"]: n.get("role") for n in view["nodes"] if n["type"] == "Method"}
    assert roles == {"Method:gcn": "proposed", "Method:gat": "baseline", "Method:mlp": "used"}