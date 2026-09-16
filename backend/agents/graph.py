"""
Wires the individual nodes into one LangGraph StateGraph: search -> filter
-> ingest -> summarize, run sequentially for one topic.
"""
from langgraph.graph import END, StateGraph

from agents.nodes import filter_node, ingest_node, search_node, summarize_node
from agents.state import AgentState


def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("search", search_node)
    graph.add_node("filter", filter_node)
    graph.add_node("ingest", ingest_node)
    graph.add_node("summarize", summarize_node)

    graph.set_entry_point("search")
    graph.add_edge("search", "filter")
    graph.add_edge("filter", "ingest")
    graph.add_edge("ingest", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()


_compiled_graph = None


def get_agent_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_agent_graph()
    return _compiled_graph