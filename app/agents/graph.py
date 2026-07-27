"""The multi-agent LangGraph: supervisor routes, workers retrieve, synthesis answers.

Runs today with stubs so you can see the full flow, then replace each node with
real logic week by week. Because `trace` has an `operator.add` reducer in
state.py, each node returns only ITS OWN trace additions and LangGraph merges
them -- this is what makes the parallel "both" route work correctly.
"""

from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.state import AgentState
from app.core.redaction import redact
from app.retrieval.graph import GraphRetriever
from app.retrieval.vector import VectorRetriever

_graph_retriever = GraphRetriever()
_vector_retriever = VectorRetriever()


def redact_node(state: AgentState) -> AgentState:
    q = state["question"]
    return {"redacted_question": redact(q), "trace": ["redacted input"]}


def supervisor_node(state: AgentState) -> AgentState:
    """Decide the retrieval route.

    TODO(week2): replace heuristic with an LLM router that reads the question
    and picks graph / vector / both, with a justification added to the trace.
    """
    q = state["redacted_question"]
    route: Literal["graph", "vector", "both"] = "both" if "?" in q else "vector"
    return {"route": route, "trace": [f"supervisor chose route={route}"]}


def graph_agent_node(state: AgentState) -> AgentState:
    ctx = _graph_retriever.retrieve(state["redacted_question"])
    return {"graph_context": ctx, "trace": ["graph agent ran"]}


def vector_agent_node(state: AgentState) -> AgentState:
    ctx = _vector_retriever.retrieve(state["redacted_question"])
    return {"vector_context": ctx, "trace": ["vector agent ran"]}


def synthesis_node(state: AgentState) -> AgentState:
    """Combine retrieved context into a final answer.

    TODO(week2): real LLM synthesis over graph_context + vector_context.
    TODO(week5): compute a real RAGAS faithfulness score here.
    """
    parts = [state.get("graph_context", ""), state.get("vector_context", "")]
    answer = "SYNTHESISED ANSWER from: " + " | ".join(p for p in parts if p)
    return {"answer": answer, "faithfulness": None, "trace": ["synthesis complete"]}


def _route(state: AgentState) -> list[str]:
    """Conditional edge: fan out to the agents the supervisor selected."""
    route = state["route"]
    if route == "graph":
        return ["graph_agent"]
    if route == "vector":
        return ["vector_agent"]
    return ["graph_agent", "vector_agent"]


def build_graph() -> CompiledStateGraph:
    g = StateGraph(AgentState)
    g.add_node("redact", redact_node)
    g.add_node("supervisor", supervisor_node)
    g.add_node("graph_agent", graph_agent_node)
    g.add_node("vector_agent", vector_agent_node)
    g.add_node("synthesis", synthesis_node)

    g.set_entry_point("redact")
    g.add_edge("redact", "supervisor")
    g.add_conditional_edges(
        "supervisor", _route, {"graph_agent": "graph_agent", "vector_agent": "vector_agent"}
    )
    g.add_edge("graph_agent", "synthesis")
    g.add_edge("vector_agent", "synthesis")
    g.add_edge("synthesis", END)
    return g.compile()


compiled_graph = build_graph()
