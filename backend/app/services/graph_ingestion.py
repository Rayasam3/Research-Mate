"""
Writes a paper's structured PaperRecord into Neo4j. MERGE (never CREATE)
throughout, so re-indexing a paper is safe and never duplicates nodes.
Only the Paper node is user-scoped; methods, datasets and domains are
shared knowledge.
"""
import logging
from typing import Any

from app.schemas.paper_record import MethodMention, PaperRecord
from app.services.graph_client import run_query
from app.services.graph_schema import normalize_key, statement_key

logger = logging.getLogger(__name__)

_ROLE_PRIORITY = {"proposed": 0, "baseline": 1, "used": 2}


def _collect(record: PaperRecord):
    """Return (methods, datasets, results) as de-duplicated, keyed dicts."""
    methods: dict[str, dict] = {}
    for m in record.methods:
        key = normalize_key(m.name)
        if not key:
            continue
        current = methods.get(key)
        if current is None or _ROLE_PRIORITY[m.role] < _ROLE_PRIORITY[current["role"]]:
            methods[key] = {"key": key, "name": m.name.strip(), "role": m.role, "novelty": m.novelty}

    datasets: dict[str, dict] = {}
    for name in record.datasets:
        key = normalize_key(name)
        if key:
            datasets.setdefault(key, {"key": key, "name": name.strip()})

    results = []
    for r in record.results:
        mk, dk = normalize_key(r.method), normalize_key(r.dataset)
        if not mk or not dk:
            continue
        # A result implies its method and dataset exist.
        methods.setdefault(mk, {"key": mk, "name": r.method.strip(), "role": "used", "novelty": None})
        datasets.setdefault(dk, {"key": dk, "name": r.dataset.strip()})
        results.append(
            {"method_key": mk, "dataset_key": dk, "metric": r.metric or "", "value": r.value or ""}
        )
    return list(methods.values()), list(datasets.values()), results


def _statements(paper_id: str, texts: list[str]) -> list[dict]:
    items = {}
    for text in texts:
        text = (text or "").strip()[:500]
        if text:
            items[statement_key(paper_id, text)] = {"key": statement_key(paper_id, text), "text": text}
    return list(items.values())


async def index_record_in_graph(
    paper_id: str, paper: Any, record: PaperRecord, user_id: str | None
) -> dict:
    await run_query(
        """
        MERGE (p:Paper {paper_id: $paper_id})
        SET p.title = $title, p.year = $year, p.source = $source, p.user_id = $user_id,
            p.citations = $citations
        """,
        {
            "paper_id": paper_id,
            "title": paper.title,
            "year": paper.published_date.year if paper.published_date else None,
            "source": paper.source.value,
            "user_id": user_id,
            "citations": getattr(paper, "citation_count", None),
        },
    )

    authors = [a.strip() for a in paper.authors if a and a.strip()]
    if authors:
        await run_query(
            """
            MATCH (p:Paper {paper_id: $paper_id})
            UNWIND $authors AS author_name
            MERGE (a:Author {name: author_name})
            MERGE (a)-[:AUTHORED]->(p)
            """,
            {"paper_id": paper_id, "authors": authors},
        )

    methods, datasets, results = _collect(record)

    if methods:
        await run_query(
            """
            MATCH (p:Paper {paper_id: $paper_id})
            UNWIND $methods AS m
            MERGE (x:Method {key: m.key})
              ON CREATE SET x.name = m.name
            MERGE (p)-[r:USES_METHOD]->(x)
            SET r.role = m.role, r.novelty = m.novelty
            """,
            {"paper_id": paper_id, "methods": methods},
        )

    if datasets:
        await run_query(
            """
            MATCH (p:Paper {paper_id: $paper_id})
            UNWIND $datasets AS d
            MERGE (x:Dataset {key: d.key})
              ON CREATE SET x.name = d.name
            MERGE (p)-[:EVALUATED_ON]->(x)
            """,
            {"paper_id": paper_id, "datasets": datasets},
        )

    if results:
        await run_query(
            """
            UNWIND $results AS res
            MATCH (m:Method {key: res.method_key})
            MATCH (d:Dataset {key: res.dataset_key})
            MERGE (m)-[t:TESTED_ON {paper_id: $paper_id, metric: res.metric}]->(d)
            SET t.value = res.value
            """,
            {"paper_id": paper_id, "results": results},
        )

    for label, rel, value in (
        ("Domain", "IN_DOMAIN", record.domain),
        ("Task", "ADDRESSES_TASK", record.task),
    ):
        key = normalize_key(value) if value else ""
        if key:
            await run_query(
                f"""
                MATCH (p:Paper {{paper_id: $paper_id}})
                MERGE (n:{label} {{key: $key}})
                  ON CREATE SET n.name = $name
                MERGE (p)-[:{rel}]->(n)
                """,
                {"paper_id": paper_id, "key": key, "name": value.strip()},
            )

    limitations = _statements(paper_id, record.limitations)
    if limitations:
        await run_query(
            """
            MATCH (p:Paper {paper_id: $paper_id})
            UNWIND $items AS it
            MERGE (l:Limitation {key: it.key})
              ON CREATE SET l.text = it.text
            MERGE (p)-[:STATES_LIMITATION]->(l)
            """,
            {"paper_id": paper_id, "items": limitations},
        )

    future_work = _statements(paper_id, record.future_work)
    if future_work:
        await run_query(
            """
            MATCH (p:Paper {paper_id: $paper_id})
            UNWIND $items AS it
            MERGE (f:FutureWork {key: it.key})
              ON CREATE SET f.text = it.text
            MERGE (p)-[:SUGGESTS_FUTURE_WORK]->(f)
            """,
            {"paper_id": paper_id, "items": future_work},
        )

    counts = {
        "authors": len(authors),
        "methods": len(methods),
        "datasets": len(datasets),
        "results": len(results),
        "limitations": len(limitations),
        "future_work": len(future_work),
    }
    logger.info(
        "Indexed paper_id=%s in graph: %d authors, %d methods, %d datasets, "
        "%d results, %d limitations, %d future-work",
        paper_id, counts["authors"], counts["methods"], counts["datasets"],
        counts["results"], counts["limitations"], counts["future_work"],
    )
    return counts


async def index_paper_in_graph(
    paper_id: str, paper: Any, methods: list[str], datasets: list[str], user_id: str | None
) -> dict:
    """Backward-compatible wrapper for the current one-chunk extraction."""
    record = PaperRecord(
        methods=[MethodMention(name=m) for m in methods],
        datasets=list(datasets),
    )
    return await index_record_in_graph(paper_id, paper, record, user_id)