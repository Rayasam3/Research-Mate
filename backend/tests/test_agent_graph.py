from agents.graph import build_agent_graph


def test_agent_graph_has_correct_node_order():
    """
    Confirms the graph wires nodes in the correct sequence: search -> filter
    -> ingest -> summarize -> END. Testing the graph's structure directly
    avoids fighting monkeypatch's import-time binding, which doesn't work
    across the module boundary the way you'd expect (nodes are captured by
    reference when the graph is built, before any test patch can apply).
    """
    graph = build_agent_graph()
    graph_structure = graph.get_graph()

    node_names = set(graph_structure.nodes.keys())
    assert {"search", "filter", "ingest", "summarize"}.issubset(node_names)

    edges = {(edge.source, edge.target) for edge in graph_structure.edges}
    assert ("search", "filter") in edges
    assert ("filter", "ingest") in edges
    assert ("ingest", "summarize") in edges


def test_agent_graph_compiles_without_error():
    """A basic smoke test that the graph definition itself is valid."""
    graph = build_agent_graph()
    assert graph is not None