"""
Builds a small node/link list of the knowledge graph for the frontend's
"Knowledge Graph" tab. It uses the same nodes and relationships that you
can see in the Neo4j console, so the picture in the app and the picture in
Neo4j always match.
"""
from app.services.graph_client import run_query

# (relationship, from label, to label, extra field on the relationship)
_EDGE_QUERIES = [
    ("USES_METHOD", "Paper", "Method"),
    ("EVALUATED_ON", "Paper", "Dataset"),
    ("IN_DOMAIN", "Paper", "Domain"),
    ("ADDRESSES_TASK", "Paper", "Task"),
]


async def get_graph_view(paper_ids: list[str], user_id: str) -> dict:
    nodes: dict[str, dict] = {}
    links: list[dict] = []

    papers = await run_query(
        "MATCH (p:Paper) WHERE p.paper_id IN $ids AND p.user_id = $uid "
        "RETURN p.paper_id AS id, p.title AS name, p.year AS year",
        {"ids": paper_ids, "uid": user_id},
    )
    for p in papers:
        nodes[p["id"]] = {"id": p["id"], "name": p["name"], "type": "Paper", "year": p["year"]}
    if not nodes:
        return {"nodes": [], "links": []}

    for rel, _, label in _EDGE_QUERIES:
        rows = await run_query(
            f"""
            MATCH (p:Paper)-[r:{rel}]->(x:{label})
            WHERE p.paper_id IN $ids AND p.user_id = $uid
            RETURN p.paper_id AS source, x.key AS key, x.name AS name, r.role AS role
            """,
            {"ids": paper_ids, "uid": user_id},
        )
        for row in rows:
            node_id = f"{label}:{row['key']}"
            nodes.setdefault(node_id, {"id": node_id, "name": row["name"], "type": label})
            links.append({"source": row["source"], "target": node_id, "type": rel, "role": row["role"]})

    # Each method gets ONE role for the picture: "proposed" if any paper proposes it,
    # else "baseline" if any paper compares against it, else "used".
    order = {"proposed": 0, "baseline": 1}
    for link in links:
        if link["type"] == "USES_METHOD":
            node = nodes[link["target"]]
            role = link.get("role") or "used"
            if order.get(role, 2) < order.get(node.get("role"), 3):
                node["role"] = role
                
    # Method -> Dataset results reported in the papers
    tested = await run_query(
        """
        MATCH (m:Method)-[t:TESTED_ON]->(d:Dataset)
        WHERE t.paper_id IN $ids
        RETURN m.key AS m, d.key AS d, t.metric AS metric, t.value AS value
        """,
        {"ids": paper_ids},
    )
    for row in tested:
        source, target = f"Method:{row['m']}", f"Dataset:{row['d']}"
        if source in nodes and target in nodes:
            links.append(
                {"source": source, "target": target, "type": "TESTED_ON", "metric": row["metric"], "value": row["value"]}
            )

    # Gap candidates found by the gap analysis
    gaps = await run_query(
        """
        MATCH (g:Gap {user_id: $uid})-[:ABOUT_METHOD]->(m:Method)
        MATCH (g)-[:ABOUT_DATASET]->(d:Dataset)
        RETURN g.key AS key, g.text AS text, g.strength AS strength, m.key AS m, d.key AS d
        """,
        {"uid": user_id},
    )
    for row in gaps:
        m_id, d_id = f"Method:{row['m']}", f"Dataset:{row['d']}"
        if m_id in nodes and d_id in nodes:
            gap_id = f"Gap:{row['key']}"
            nodes[gap_id] = {"id": gap_id, "name": "Gap", "type": "Gap", "detail": row["text"], "strength": row["strength"]}
            links.append({"source": gap_id, "target": m_id, "type": "ABOUT_METHOD"})
            links.append({"source": gap_id, "target": d_id, "type": "ABOUT_DATASET"})

    return {"nodes": list(nodes.values()), "links": links}
