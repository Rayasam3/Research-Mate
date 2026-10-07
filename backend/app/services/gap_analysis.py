"""
Phase 4: finding research-gap CANDIDATES from the knowledge graph.

An old idea was "few connections = research gap". That is not valid: a
method can have few connections because it is outdated or weak. So we do
NOT call anything a gap just because it is rare. Instead we look for two
kinds of evidence and always show that evidence to the user:

1. Untested combinations. A core method (proposed / baseline in some paper)
   and a dataset that other papers use, where no paper has used them
   together. Ranked by how well-used both sides are, how recent and how
   cited the papers are. Weak or outdated cases are labelled as such.

2. Author-stated gaps. Limitations and future work that the authors
   themselves wrote in their papers (read from the full text in Phase 2).

Everything here is plain Python over graph data - no LLM is used, so a gap
can never be invented. A "candidate gap" is a lead for the researcher to
check, not a proven fact.
"""
import logging
import math
import re
from datetime import date

from app.services.graph_client import run_query

logger = logging.getLogger(__name__)

MAX_COMBINATIONS = 10
MAX_STATEMENTS = 8
CORE_ROLES = ("proposed", "baseline")  # "used" methods are tools (e.g. Adam), not research methods

_PAPERS_QUERY = """
MATCH (p:Paper)
WHERE p.paper_id IN $paper_ids AND p.user_id = $user_id
OPTIONAL MATCH (p)-[um:USES_METHOD]->(m:Method)
WITH p, collect(DISTINCT {key: m.key, name: m.name, role: um.role}) AS methods
OPTIONAL MATCH (p)-[:EVALUATED_ON]->(d:Dataset)
WITH p, methods, collect(DISTINCT {key: d.key, name: d.name}) AS datasets
OPTIONAL MATCH (p)-[:STATES_LIMITATION]->(l:Limitation)
WITH p, methods, datasets, collect(DISTINCT l.text) AS limitations
OPTIONAL MATCH (p)-[:SUGGESTS_FUTURE_WORK]->(f:FutureWork)
RETURN p.paper_id AS paper_id, p.title AS title, p.year AS year, p.citations AS citations,
       methods, datasets, limitations, collect(DISTINCT f.text) AS future_work
"""

_TESTED_QUERY = """
MATCH (m:Method)-[t:TESTED_ON]->(d:Dataset)
WHERE t.paper_id IN $paper_ids
RETURN m.key AS method_key, d.key AS dataset_key
"""

_STORE_QUERY = """
UNWIND $gaps AS g
MATCH (m:Method {key: g.method_key})
MATCH (d:Dataset {key: g.dataset_key})
MERGE (x:Gap {key: g.key})
SET x.text = g.text, x.strength = g.strength, x.score = g.score, x.user_id = $user_id
MERGE (x)-[:ABOUT_METHOD]->(m)
MERGE (x)-[:ABOUT_DATASET]->(d)
WITH x, g
UNWIND g.paper_ids AS pid
MATCH (p:Paper {paper_id: pid})
MERGE (x)-[:SUPPORTED_BY]->(p)
"""


def _clean(items: list[dict]) -> list[dict]:
    """Neo4j's collect() returns [{key: None}] when nothing matched - drop those."""
    return [i for i in items if i.get("key")]


def _mentions(text: str, name: str) -> bool:
    return len(name) >= 3 and re.search(r"\b" + re.escape(name.lower()) + r"\b", text.lower()) is not None


def build_gaps(papers: list[dict], tested_pairs: set[tuple[str, str]], this_year: int | None = None) -> dict:
    """
    Pure function: turns paper data into gap candidates (easy to test).
    `papers` rows look like the output of _PAPERS_QUERY.
    """
    this_year = this_year or date.today().year

    methods: dict[str, dict] = {}   # key -> {name, papers, proposed}
    datasets: dict[str, dict] = {}  # key -> {name, papers}
    covered: set[tuple[str, str]] = set(tested_pairs)

    for paper in papers:
        paper_methods = _clean(paper["methods"])
        paper_datasets = _clean(paper["datasets"])
        for m in paper_methods:
            if m.get("role") in CORE_ROLES:
                entry = methods.setdefault(m["key"], {"name": m["name"], "papers": [], "proposed": False})
                entry["papers"].append(paper)
                entry["proposed"] = entry["proposed"] or m.get("role") == "proposed"
        for d in paper_datasets:
            datasets.setdefault(d["key"], {"name": d["name"], "papers": []})["papers"].append(paper)
        # A paper that uses a method and a dataset together has "tested" that pair.
        for m in paper_methods:
            for d in paper_datasets:
                covered.add((m["key"], d["key"]))

    # All statements the authors wrote - used to confirm gap candidates.
    statements = [
        (kind, text, p)
        for p in papers
        for kind, texts in (("future_work", p["future_work"]), ("limitation", p["limitations"]))
        for text in texts
        if text
    ]

    combos = []
    for mkey, m in methods.items():
        for dkey, d in datasets.items():
            if (mkey, dkey) in covered:
                continue
            support_m, support_d = len(m["papers"]), len(d["papers"])
            newest = max((p["year"] or 0) for p in m["papers"])
            best_citations = max((p["citations"] or 0) for p in m["papers"] + d["papers"])

            recent = max(0.0, 1 - (this_year - newest) / 10) if newest else 0.0
            cited = min(math.log10(1 + best_citations) / 4, 1.0)
            score = min(support_m, 3) + min(support_d, 3) + recent + 0.5 * cited + (0.5 if m["proposed"] else 0)

            if support_m >= 2 and support_d >= 2:
                strength = "strong"
            elif support_m >= 2 or support_d >= 2:
                strength = "moderate"
            else:
                strength = "weak"

            caveats = []
            if newest and newest <= this_year - 5:
                caveats.append(f"The method was last seen in {newest}; it may be outdated rather than neglected.")
            if strength == "weak":
                caveats.append("Only one paper on each side - treat this as a lead to check, not a conclusion.")

            hint = next(
                (
                    {"kind": kind, "text": text, "paper_title": p["title"]}
                    for kind, text, p in statements
                    if _mentions(text, m["name"]) or _mentions(text, d["name"])
                ),
                None,
            )
            if hint:
                score += 1.0   # the authors themselves point at it

            combos.append(
                {
                    "key": f"{mkey}|{dkey}",
                    "method_key": mkey,
                    "dataset_key": dkey,
                    "method": m["name"],
                    "dataset": d["name"],
                    "statement": (
                        f"{m['name']} (core method in {support_m} paper{'s' if support_m != 1 else ''}) "
                        f"has not been evaluated on {d['name']} "
                        f"(used in {support_d} paper{'s' if support_d != 1 else ''}) in this set."
                    ),
                    "strength": strength,
                    "score": round(score, 2),
                    "method_evidence": [{"title": p["title"], "year": p["year"]} for p in m["papers"]],
                    "dataset_evidence": [{"title": p["title"], "year": p["year"]} for p in d["papers"]],
                    "author_hint": hint,
                    "caveats": caveats,
                    "paper_ids": sorted({p["paper_id"] for p in m["papers"] + d["papers"]}),
                }
            )

    combos.sort(key=lambda c: c["score"], reverse=True)

    def stated(kind: str) -> list[dict]:
        rows = [
            {
                "text": text,
                "paper_id": p["paper_id"],
                "paper_title": p["title"],
                "year": p["year"],
                "citations": p["citations"],
            }
            for k, text, p in statements
            if k == kind
        ]
        rows.sort(key=lambda r: ((r["year"] or 0), (r["citations"] or 0)), reverse=True)
        return rows[:MAX_STATEMENTS]

    return {
        "untested_combinations": combos[:MAX_COMBINATIONS],
        "future_work": stated("future_work"),
        "limitations": stated("limitation"),
        "summary": {
            "papers": len(papers),
            "core_methods": len(methods),
            "datasets": len(datasets),
            "pairs_not_tested": len(combos),
        },
    }


async def _store_gaps(user_id: str, combos: list[dict]) -> None:
    """Save the gap candidates as Gap nodes so they can be seen in the Neo4j console."""
    if not combos:
        return
    gaps = [
        {
            "key": f"{user_id}:{c['key']}",
            "method_key": c["method_key"],
            "dataset_key": c["dataset_key"],
            "text": c["statement"],
            "strength": c["strength"],
            "score": c["score"],
            "paper_ids": c["paper_ids"],
        }
        for c in combos
    ]
    await run_query(_STORE_QUERY, {"gaps": gaps, "user_id": user_id})


async def analyze_gaps(paper_ids: list[str], user_id: str) -> dict:
    papers = await run_query(_PAPERS_QUERY, {"paper_ids": paper_ids, "user_id": user_id})
    tested_rows = await run_query(_TESTED_QUERY, {"paper_ids": [p["paper_id"] for p in papers]})
    tested = {(r["method_key"], r["dataset_key"]) for r in tested_rows}

    result = build_gaps(papers, tested)

    try:
        await _store_gaps(user_id, result["untested_combinations"])
    except Exception:
        logger.exception("Could not store Gap nodes (results are still returned)")
    return result
