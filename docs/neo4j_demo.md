# Showing the knowledge graph in the Neo4j console

1. Open https://console.neo4j.io, resume the instance if it is paused, and open the **Query** tool.
2. Run the queries from `docs/neo4j_demo_queries.cypher` one at a time.
3. Switch the result to the **Graph** view. Click a node type (Paper, Method, ...) in the panel on the right to change its colour, size and caption.

Suggested look:

| Node type | Colour | Caption (property) |
|-----------|--------|--------------------|
| Paper | blue, large | `title` |
| Method | green | `name` |
| Dataset | orange | `name` |
| Domain | purple | `name` |
| Task | teal | `name` |
| Gap | red | `strength` |
| Limitation / FutureWork | grey, small | `text` |

Good order for a demo: query 13 (counts) -> 2 (clean graph) -> 4 (results) -> 9 (what is different) -> 6 (gaps with evidence) -> 10 (author statements).
