"""The multi-agent LangGraph: supervisor routes, workers retrieve, synthesis
answers, grader checks, and a bounded repair loop retries on ungrounded answers.

    redact -> supervisor -> (graph_agent | vector_agent | both) -> synthesis
           -> grader -> {repair -> supervisor ...  |  END}

Because `trace` has an `operator.add` reducer, each node returns only ITS OWN
trace additions and LangGraph merges them -- this is what makes the parallel
"both" route work. Prompt filling uses str.replace (not .format) so retrieved
context containing literal { } braces can never break templating.
"""

import re
from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.prompts import load_prompt
from app.agents.schemas import GroundingVerdict, RouteDecision
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.llm import get_llm
from app.core.redaction import redact
from app.retrieval.graph import GraphRetriever
from app.retrieval.vector import VectorRetriever

_graph_retriever = GraphRetriever()
_vector_retriever = VectorRetriever()

_CITATION = re.compile(r"\[([^\]]+)\]")


def _fill(template: str, **kw: str) -> str:
    """Substitute {key} placeholders WITHOUT str.format, so literal braces in
    the injected values (e.g. Cypher-ish context) are left untouched."""
    for k, v in kw.items():
        template = template.replace("{" + k + "}", v)
    return template


def redact_node(state: AgentState) -> AgentState:
    q = state["question"]
    return {"redacted_question": redact(q), "trace": ["redacted input"]}


def supervisor_node(state: AgentState) -> AgentState:
    """LLM router: pick graph / vector / both with a justification.

    On a repair retry (retries > 0) we broaden to "both" to gather more context.
    On any LLM failure we fall back to a deterministic heuristic so routing never
    hard-crashes the request.
    """
    if state.get("retries", 0) > 0:
        return {
            "route": "both",
            "route_reason": "repair retry: broadening to both stores",
            "trace": ["supervisor: repair -> route=both"],
        }

    q = state["redacted_question"]
    try:
        llm = get_llm().with_structured_output(RouteDecision)
        decision: RouteDecision = llm.invoke(_fill(load_prompt("router"), question=q))  # type: ignore[assignment]
        return {
            "route": decision.route,
            "route_reason": decision.reason,
            "trace": [f"supervisor: route={decision.route} ({decision.reason})"],
        }
    except Exception as e:  # noqa: BLE001
        route: Literal["graph", "vector", "both"] = "both" if "?" in q else "vector"
        return {
            "route": route,
            "route_reason": f"fallback heuristic (router LLM failed: {type(e).__name__})",
            "trace": [f"supervisor fallback: route={route}"],
        }


def graph_agent_node(state: AgentState) -> AgentState:
    """Retrieve from Neo4j; degrade to empty context on failure (recorded in trace)."""
    try:
        ctx = _graph_retriever.retrieve(state["redacted_question"])
        return {"graph_context": ctx, "trace": ["graph agent ran"]}
    except Exception as e:  # noqa: BLE001
        return {"graph_context": "", "trace": [f"graph agent error: {type(e).__name__}"]}


def vector_agent_node(state: AgentState) -> AgentState:
    """Retrieve from Qdrant; degrade to empty context on failure (recorded in trace)."""
    try:
        ctx = _vector_retriever.retrieve(state["redacted_question"])
        return {"vector_context": ctx, "trace": ["vector agent ran"]}
    except Exception as e:  # noqa: BLE001
        return {"vector_context": "", "trace": [f"vector agent error: {type(e).__name__}"]}


def synthesis_node(state: AgentState) -> AgentState:
    """LLM answer over retrieved context only, with inline [title] citations."""
    q = state["redacted_question"]
    gc = state.get("graph_context") or "(none)"
    vc = state.get("vector_context") or "(none)"
    try:
        prompt = _fill(load_prompt("synthesis"), question=q, graph_context=gc, vector_context=vc)
        answer = str(get_llm().invoke(prompt).content).strip()
    except Exception as e:  # noqa: BLE001
        return {"answer": "", "citations": [], "trace": [f"synthesis error: {type(e).__name__}"]}
    citations = sorted(set(_CITATION.findall(answer)))
    return {
        "answer": answer,
        "citations": citations,
        "faithfulness": None,  # real RAGAS score wired in Phase 5
        "trace": [f"synthesis complete ({len(citations)} citations)"],
    }


def grader_node(state: AgentState) -> AgentState:
    """LLM-as-judge: is the answer fully supported by the retrieved context?"""
    answer = state.get("answer", "")
    if not answer:
        return {
            "grounded": False,
            "grader_reason": "empty answer",
            "trace": ["grader: ungrounded (empty)"],
        }

    context = (
        (state.get("graph_context") or "") + "\n" + (state.get("vector_context") or "")
    ).strip()
    try:
        llm = get_llm().with_structured_output(GroundingVerdict)
        prompt = _fill(
            load_prompt("grader"),
            question=state["redacted_question"],
            context=context or "(none)",
            answer=answer,
        )
        verdict: GroundingVerdict = llm.invoke(prompt)  # type: ignore[assignment]
        return {
            "grounded": verdict.grounded,
            "grader_reason": verdict.reason,
            "trace": [f"grader: grounded={verdict.grounded} ({verdict.reason})"],
        }
    except Exception as e:  # noqa: BLE001
        # Fail-open: a grader failure shouldn't block the answer or spin the loop.
        return {
            "grounded": True,
            "grader_reason": f"grader error, passing ({type(e).__name__})",
            "trace": ["grader error: passing"],
        }


def repair_node(state: AgentState) -> AgentState:
    """Increment the retry counter; supervisor will broaden retrieval next pass."""
    retries = state.get("retries", 0) + 1
    return {"retries": retries, "trace": [f"repair: retry {retries}"]}


def _route(state: AgentState) -> list[str]:
    """Conditional edge: fan out to the agents the supervisor selected."""
    route = state["route"]
    if route == "graph":
        return ["graph_agent"]
    if route == "vector":
        return ["vector_agent"]
    return ["graph_agent", "vector_agent"]


def _after_grader(state: AgentState) -> str:
    """Repair if ungrounded and retries remain; otherwise finish (gracefully)."""
    if state.get("grounded"):
        return "end"
    if state.get("retries", 0) >= get_settings().max_retries:
        return "end"
    return "repair"


def build_graph() -> CompiledStateGraph:
    g = StateGraph(AgentState)
    g.add_node("redact", redact_node)
    g.add_node("supervisor", supervisor_node)
    g.add_node("graph_agent", graph_agent_node)
    g.add_node("vector_agent", vector_agent_node)
    g.add_node("synthesis", synthesis_node)
    g.add_node("grader", grader_node)
    g.add_node("repair", repair_node)

    g.set_entry_point("redact")
    g.add_edge("redact", "supervisor")
    g.add_conditional_edges(
        "supervisor", _route, {"graph_agent": "graph_agent", "vector_agent": "vector_agent"}
    )
    g.add_edge("graph_agent", "synthesis")
    g.add_edge("vector_agent", "synthesis")
    g.add_edge("synthesis", "grader")
    g.add_conditional_edges("grader", _after_grader, {"repair": "repair", "end": END})
    g.add_edge("repair", "supervisor")
    return g.compile()


compiled_graph = build_graph()
