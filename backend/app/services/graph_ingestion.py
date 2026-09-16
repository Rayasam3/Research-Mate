"""
Writes a paper and its extracted entities (authors, methods, datasets)
into the Neo4j graph as nodes and relationships.
"""
import logging

from app.schemas.paper import Paper
from app.services.graph_client import run_query

logger = logging.getLogger(__name__)


async def index_paper_in_graph(paper_id: str, paper: Paper, methods: list[str], datasets: list[str]) -> dict:
    """
    Merges (creates if absent, reuses if present) the Paper node, Author
    nodes, Method nodes, and Dataset nodes, and connects them with
    relationships. MERGE (not CREATE) throughout, so re-indexing the same
    paper is safe and never duplicates nodes.
    """
    await run_query(
        """
        MERGE (p:Paper {paper_id: $paper_id})
        SET p.title = $title, p.year = $year, p.source = $source
        """,
        {
            "paper_id": paper_id,
            "title": paper.title,
            "year": paper.published_date.year if paper.published_date else None,
            "source": paper.source.value,
        },
    )

    for author in paper.authors:
        await run_query(
            """
            MERGE (a:Author {name: $name})
            MERGE (p:Paper {paper_id: $paper_id})
            MERGE (a)-[:AUTHORED]->(p)
            """,
            {"name": author, "paper_id": paper_id},
        )

    for method in methods:
        await run_query(
            """
            MERGE (m:Method {name: $name})
            MERGE (p:Paper {paper_id: $paper_id})
            MERGE (p)-[:USES_METHOD]->(m)
            """,
            {"name": method, "paper_id": paper_id},
        )

    for dataset in datasets:
        await run_query(
            """
            MERGE (d:Dataset {name: $name})
            MERGE (p:Paper {paper_id: $paper_id})
            MERGE (p)-[:EVALUATED_ON]->(d)
            """,
            {"name": dataset, "paper_id": paper_id},
        )

    logger.info(
        "Indexed paper_id=%s in graph: %d authors, %d methods, %d datasets",
        paper_id,
        len(paper.authors),
        len(methods),
        len(datasets),
    )
    return {"paper_id": paper_id, "methods": methods, "datasets": datasets}