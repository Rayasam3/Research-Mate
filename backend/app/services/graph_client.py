"""
Wraps the official Neo4j async driver as a module-level singleton. All
graph reads/writes for Phase 5 go through this - nothing else in the app
should import neo4j directly.
"""
import logging

from neo4j import AsyncGraphDatabase

from app.core.config import settings

logger = logging.getLogger(__name__)

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_lifetime=300,  # recycle connections every 5 min
            liveness_check_timeout=30,     # verify connection is alive before reuse
        )
    return _driver


async def run_query(query: str, params: dict | None = None) -> list[dict]:
    """
    Runs a Cypher query and returns results as a list of plain dicts.
    Centralizing this here means every caller gets the same error
    handling and result-shape conversion.
    """
    driver = get_driver()
    try:
        async with driver.session(database=settings.neo4j_database) as session:
            result = await session.run(query, params or {})
            records = await result.data()
            return records
    except Exception:
        logger.exception("Neo4j query failed: %s", query)
        raise


async def ensure_constraints() -> None:
    """
    Creates uniqueness constraints so re-running ingestion never creates
    duplicate nodes for the same paper/method/dataset. Safe to call
    repeatedly - Neo4j no-ops if a constraint already exists.
    """
    constraints = [
        "CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.paper_id IS UNIQUE",
        "CREATE CONSTRAINT method_name IF NOT EXISTS FOR (m:Method) REQUIRE m.name IS UNIQUE",
        "CREATE CONSTRAINT dataset_name IF NOT EXISTS FOR (d:Dataset) REQUIRE d.name IS UNIQUE",
        "CREATE CONSTRAINT author_name IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE",
    ]
    for constraint in constraints:
        await run_query(constraint)