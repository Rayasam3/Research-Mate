import pytest

from app.services import gap_analysis
from app.services.gap_analysis import build_gaps


def _paper(pid, title, year, methods, datasets, limitations=(), future=(), citations=None):
    return {
        "paper_id": pid,
        "title": title,
        "year": year,
        "citations": citations,
        "methods": [{"key": k, "name": k.upper(), "role": role} for k, role in methods],
        "datasets": [{"key": k, "name": k.upper()} for k in datasets],
        "limitations": list(limitations),
        "future_work": list(future),
    }


def test_untested_pair_is_found():
    papers = [
        _paper("p1", "Paper 1", 2024, [("gcn", "proposed")], ["cora"]),
        _paper("p2", "Paper 2", 2023, [("gat", "proposed")], ["pubmed"]),
    ]
    result = build_gaps(papers, set(), this_year=2025)
    pairs = {(c["method"], c["dataset"]) for c in result["untested_combinations"]}
    # GCN was never tried on PUBMED and GAT never on CORA.
    assert pairs == {("GCN", "PUBMED"), ("GAT", "CORA")}


def test_pair_tested_together_is_not_a_gap():
    papers = [_paper("p1", "Paper 1", 2024, [("gcn", "proposed")], ["cora", "pubmed"])]
    assert build_gaps(papers, set(), this_year=2025)["untested_combinations"] == []


def test_pair_in_tested_on_results_is_not_a_gap():
    papers = [
        _paper("p1", "Paper 1", 2024, [("gcn", "proposed")], ["cora"]),
        _paper("p2", "Paper 2", 2023, [("gat", "proposed")], ["pubmed"]),
    ]
    tested = {("gcn", "pubmed"), ("gat", "cora")}
    assert build_gaps(papers, tested, this_year=2025)["untested_combinations"] == []


def test_tool_methods_are_not_gap_candidates():
    papers = [
        _paper("p1", "Paper 1", 2024, [("adam", "used")], ["cora"]),
        _paper("p2", "Paper 2", 2023, [("gat", "proposed")], ["pubmed"]),
    ]
    methods = {c["method"] for c in build_gaps(papers, set(), this_year=2025)["untested_combinations"]}
    assert "ADAM" not in methods


def test_strength_and_caveats():
    papers = [
        _paper("p1", "Old", 2015, [("svm", "baseline")], ["a"]),
        _paper("p2", "New", 2024, [("gat", "proposed")], ["b"]),
    ]
    combo = build_gaps(papers, set(), this_year=2025)["untested_combinations"]
    svm = next(c for c in combo if c["method"] == "SVM")
    assert svm["strength"] == "weak"
    assert any("outdated" in c for c in svm["caveats"])      # last seen 2015
    assert any("one paper" in c for c in svm["caveats"])


def test_strong_when_both_sides_are_well_used():
    papers = [
        _paper("p1", "P1", 2024, [("gcn", "proposed")], ["cora"]),
        _paper("p2", "P2", 2024, [("gcn", "baseline")], ["cora"]),
        _paper("p3", "P3", 2024, [("sage", "proposed")], ["pubmed"]),
        _paper("p4", "P4", 2024, [("sage", "baseline")], ["pubmed"]),
    ]
    combos = build_gaps(papers, set(), this_year=2025)["untested_combinations"]
    assert combos[0]["strength"] == "strong"


def test_author_statements_are_listed_and_used_as_hint():
    papers = [
        _paper("p1", "Paper 1", 2024, [("gcn", "proposed")], ["cora"],
               limitations=["Only small graphs were used."],
               future=["We plan to test GCN on PubMed."]),
        _paper("p2", "Paper 2", 2023, [("gat", "proposed")], ["pubmed"]),
    ]
    result = build_gaps(papers, set(), this_year=2025)
    assert result["future_work"][0]["text"] == "We plan to test GCN on PubMed."
    assert result["limitations"][0]["paper_title"] == "Paper 1"
    gcn_pubmed = next(c for c in result["untested_combinations"] if c["method"] == "GCN")
    assert gcn_pubmed["author_hint"]["kind"] == "future_work"


def test_statements_sorted_newest_first():
    papers = [
        _paper("p1", "Old", 2018, [], [], future=["old idea"]),
        _paper("p2", "New", 2024, [], [], future=["new idea"]),
    ]
    texts = [f["text"] for f in build_gaps(papers, set(), this_year=2025)["future_work"]]
    assert texts == ["new idea", "old idea"]


def test_empty_input():
    result = build_gaps([], set())
    assert result["untested_combinations"] == []
    assert result["summary"]["papers"] == 0


@pytest.mark.asyncio
async def test_analyze_gaps_queries_and_stores(monkeypatch):
    calls = []

    async def fake_run_query(query, params=None):
        calls.append(query)
        if "MATCH (p:Paper)" in query and "RETURN p.paper_id" in query:
            return [
                _paper("p1", "Paper 1", 2024, [("gcn", "proposed")], ["cora"]),
                _paper("p2", "Paper 2", 2023, [("gat", "proposed")], ["pubmed"]),
            ]
        return []

    monkeypatch.setattr(gap_analysis, "run_query", fake_run_query)
    result = await gap_analysis.analyze_gaps(["p1", "p2"], "user1")
    assert len(result["untested_combinations"]) == 2
    assert any("MERGE (x:Gap" in q for q in calls)     # gaps were saved to the graph
