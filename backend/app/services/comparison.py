"""
Builds a cross-paper comparison table from graph data: for each requested
paper_id, pulls its title, year, methods, and datasets so they can be
displayed side by side.
"""
import logging

from app.services.graph_client import run_query

logger = logging.getLogger(__name__)


async def get_comparison_table(paper_ids: list[str], user_id: str | None = None) -> list[dict]:
    """
    user_id, when given, restricts results to papers owned by that user.
    Left optional so the function still works for un-authenticated
    contexts if ever needed.
    """
    if not paper_ids:
        return []

    query = """
    MATCH (p:Paper)
    WHERE p.paper_id IN $paper_ids
      AND ($user_id IS NULL OR p.user_id = $user_id)
    OPTIONAL MATCH (p)-[:USES_METHOD]->(m:Method)
    OPTIONAL MATCH (p)-[:EVALUATED_ON]->(d:Dataset)
    RETURN p.paper_id AS paper_id,
           p.title AS title,
           p.year AS year,
           collect(DISTINCT m.name) AS methods,
           collect(DISTINCT d.name) AS datasets
    """
    rows = await run_query(query, {"paper_ids": paper_ids, "user_id": user_id})
    
    # Neo4j's collect() on no matches returns [None] rather than [] - clean that up.
    for row in rows:
        row["methods"] = [m for m in row["methods"] if m]
        row["datasets"] = [d for d in row["datasets"] if d]

    return rows


async def find_related_papers(entity_type: str, entity_name: str, exclude_paper_id: str | None = None) -> list[dict]:
    """
    Finds other papers connected to the same Method or Dataset node.
    entity_type must be "method" or "dataset".
    """
    relationship = "USES_METHOD" if entity_type == "method" else "EVALUATED_ON"
    label = "Method" if entity_type == "method" else "Dataset"

    query = f"""
    MATCH (p:Paper)-[:{relationship}]->(e:{label} {{name: $entity_name}})
    WHERE $exclude_paper_id IS NULL OR p.paper_id <> $exclude_paper_id
    RETURN p.paper_id AS paper_id, p.title AS title, p.year AS year
    """
    return await run_query(query, {"entity_name": entity_name, "exclude_paper_id": exclude_paper_id})