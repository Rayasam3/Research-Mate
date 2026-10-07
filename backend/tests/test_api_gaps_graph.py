"""Calls the new endpoints end to end (Neo4j and login are faked) to check the response shapes."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.auth import get_current_user
from app.main import app
from app.services import comparison, gap_analysis, graph_view


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user1", email="a@b.c")

    async def fake_run_query(query, params=None):
        if "collect(DISTINCT f.text)" in query:   # the gap analysis query
            return [
                {"paper_id": "p1", "title": "One", "year": 2024, "citations": 3,
                 "methods": [{"key": "gcn", "name": "GCN", "role": "proposed"}],
                 "datasets": [{"key": "cora", "name": "Cora"}], "limitations": ["Small graphs only"],
                 "future_work": ["Try PubMed"]},
                {"paper_id": "p2", "title": "Two", "year": 2023, "citations": None,
                 "methods": [{"key": "gat", "name": "GAT", "role": "proposed"}],
                 "datasets": [{"key": "pubmed", "name": "PubMed"}], "limitations": [], "future_work": []},
            ]
        if "RETURN p.paper_id AS id" in query:
            return [{"id": "p1", "name": "One", "year": 2024}]
        return []

    for module in (gap_analysis, graph_view, comparison):
        monkeypatch.setattr(module, "run_query", fake_run_query)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_gaps_endpoint_shape(client):
    r = client.get("/api/gaps", params={"paper_ids": "p1,p2"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["untested_combinations"]) == 2
    first = body["untested_combinations"][0]
    assert {"method", "dataset", "statement", "strength", "caveats", "method_evidence"} <= set(first)
    assert body["future_work"][0]["text"] == "Try PubMed"
    assert body["summary"]["papers"] == 2


def test_graph_view_endpoint_shape(client):
    r = client.get("/api/graph/view", params={"paper_ids": "p1"})
    assert r.status_code == 200
    assert r.json()["nodes"][0]["type"] == "Paper"


def test_compare_endpoint_empty(client):
    r = client.get("/api/compare", params={"paper_ids": "p1"})
    assert r.status_code == 200 and r.json() == {"rows": []}
