"""
Reads the knowledge graph to compare papers side by side, and to find
other papers that share a method or dataset.

Two papers can never be published with the same contribution, so the
comparison shows what is DIFFERENT: each paper's own (proposed) methods and
what is new about them, next to the methods they share.
"""
import logging

from app.services.graph_client import run_query
from app.services.graph_schema import normalize_key

logger = logging.getLogger(__name__)

_COMPARE_QUERY = """
MATCH (p:Paper)
WHERE p.paper_id IN $paper_ids AND p.user_id = $user_id
OPTIONAL MATCH (p)-[um:USES_METHOD]->(m:Method)
WITH p, collect(DISTINCT {key: m.key, name: m.name, role: um.role, novelty: um.novelty}) AS methods
OPTIONAL MATCH (p)-[:EVALUATED_ON]->(d:Dataset)
WITH p, methods, collect(DISTINCT d.name) AS datasets
OPTIONAL MATCH (p)-[:IN_DOMAIN]->(dom:Domain)
OPTIONAL MATCH (p)-[:ADDRESSES_TASK]->(t:Task)
OPTIONAL MATCH (p)-[:STATES_LIMITATION]->(l:Limitation)
WITH p, methods, datasets, dom, t, count(DISTINCT l) AS n_limitations
OPTIONAL MATCH (p)-[:SUGGESTS_FUTURE_WORK]->(f:FutureWork)
RETURN p.paper_id AS paper_id, p.title AS title, p.year AS year, p.citations AS citations,
       methods, datasets, dom.name AS domain, t.name AS task,
       n_limitations, count(DISTINCT f) AS n_future_work
"""


async def get_comparison_table(paper_ids: list[str], user_id: str | None) -> list[dict]:
    """One row per paper. Only papers owned by `user_id` are returned."""
    if not paper_ids:
        return []

    rows = await run_query(_COMPARE_QUERY, {"paper_ids": paper_ids, "user_id": user_id})

    # How many of the compared papers use each method? (>1 means shared)
    usage: dict[str, int] = {}
    for row in rows:
        row["methods"] = [m for m in row["methods"] if m.get("key")]
        row["datasets"] = [d for d in row["datasets"] if d]
        for m in row["methods"]:
            usage[m["key"]] = usage.get(m["key"], 0) + 1

    for row in rows:
        for m in row["methods"]:
            m["shared"] = usage[m["key"]] > 1
        row["unique_methods"] = [m["name"] for m in row["methods"] if not m["shared"]]
    return rows


async def find_related_papers(
    entity_type: str, entity_name: str, user_id: str | None, exclude_paper_id: str | None = None
) -> list[dict]:
    """Other papers (of this user) connected to the same Method or Dataset."""
    relationship = "USES_METHOD" if entity_type == "method" else "EVALUATED_ON"
    label = "Method" if entity_type == "method" else "Dataset"

    query = f"""
    MATCH (p:Paper)-[:{relationship}]->(e:{label} {{key: $key}})
    WHERE p.user_id = $user_id
      AND ($exclude_paper_id IS NULL OR p.paper_id <> $exclude_paper_id)
    RETURN p.paper_id AS paper_id, p.title AS title, p.year AS year
    """
    return await run_query(
        query,
        {"key": normalize_key(entity_name), "user_id": user_id, "exclude_paper_id": exclude_paper_id},
    )
