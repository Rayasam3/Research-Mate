// =====================================================================
// Research Mate - demo queries for the Neo4j console (Query tool)
// Run ONE query at a time: paste it, press Run, then use the "Graph" view.
// =====================================================================

// ---- 1. Overview: papers and everything they connect to (no authors) ----
// Shows Paper, Method, Dataset, Domain, Task, Limitation, FutureWork.
MATCH (p:Paper)-[r]->(x)
RETURN p, r, x
LIMIT 300;

// ---- 2. Clean view: only methods, datasets, domain and task ----
MATCH (p:Paper)-[r:USES_METHOD|EVALUATED_ON|IN_DOMAIN|ADDRESSES_TASK]->(x)
RETURN p, r, x;

// ---- 3. One paper and all its neighbours (change the title text) ----
MATCH (p:Paper)
WHERE toLower(p.title) CONTAINS 'graph'
MATCH (p)-[r]-(x)
RETURN p, r, x;

// ---- 4. Results read from the papers: Method -TESTED_ON-> Dataset ----
MATCH (m:Method)-[t:TESTED_ON]->(d:Dataset)
RETURN m, t, d;

// ---- 5. Same results as a table (metric and value) ----
MATCH (m:Method)-[t:TESTED_ON]->(d:Dataset)
RETURN m.name AS method, d.name AS dataset, t.metric AS metric, t.value AS value, t.paper_id AS paper
ORDER BY dataset, method;

// ---- 6. Research-gap candidates WITH their evidence ----
// Gap -> the method and dataset that were never combined,
// and the papers that are the evidence for it.
MATCH (g:Gap)-[r]->(x)
RETURN g, r, x;

// ---- 7. Gap candidates as a table, strongest first ----
MATCH (g:Gap)-[:ABOUT_METHOD]->(m:Method), (g)-[:ABOUT_DATASET]->(d:Dataset)
RETURN g.strength AS strength, g.score AS score, m.name AS method, d.name AS dataset, g.text AS statement
ORDER BY score DESC;

// ---- 8. Papers that share a method (what they have in common) ----
MATCH (a:Paper)-[:USES_METHOD]->(m:Method)<-[:USES_METHOD]-(b:Paper)
WHERE a.paper_id < b.paper_id
RETURN a, m, b;

// ---- 9. What is DIFFERENT: the proposed method of each paper and what is new ----
MATCH (p:Paper)-[u:USES_METHOD {role: 'proposed'}]->(m:Method)
RETURN p.title AS paper, m.name AS proposed_method, u.novelty AS what_is_new
ORDER BY paper;

// ---- 10. What the authors say: limitations and future work ----
MATCH (p:Paper)-[:STATES_LIMITATION]->(l:Limitation)
RETURN p.title AS paper, 'limitation' AS kind, l.text AS statement
UNION
MATCH (p:Paper)-[:SUGGESTS_FUTURE_WORK]->(f:FutureWork)
RETURN p.title AS paper, 'future work' AS kind, f.text AS statement;

// ---- 11. Papers grouped by research field ----
MATCH (p:Paper)-[r:IN_DOMAIN]->(d:Domain)
RETURN p, r, d;

// ---- 12. Method x dataset matrix: which pairs were tried (tested = true) ----
MATCH (m:Method), (d:Dataset)
WHERE EXISTS { (m)<-[:USES_METHOD]-(:Paper)-[:EVALUATED_ON]->(d) }
   OR EXISTS { (m)-[:TESTED_ON]->(d) }
RETURN m.name AS method, d.name AS dataset, true AS tested
ORDER BY method, dataset;

// ---- 13. Sanity check: how many nodes of each type ----
MATCH (n)
RETURN labels(n)[0] AS type, count(*) AS how_many
ORDER BY how_many DESC;

// ---- 14. Delete EVERYTHING (only when you want a fresh start) ----
// MATCH (n) DETACH DELETE n;
