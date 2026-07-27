"""Unit tests for the agent nodes and repair loop — LLM mocked, no services."""

from types import SimpleNamespace

import app.agents.graph as G
from app.agents.schemas import GroundingVerdict, RouteDecision

from tests.conftest import make_llm


# --- supervisor routing -----------------------------------------------------
def test_supervisor_uses_llm_route(monkeypatch):
    monkeypatch.setattr(
        G, "get_llm", lambda: make_llm(route=RouteDecision(route="graph", reason="multi-hop"))
    )
    out = G.supervisor_node({"redacted_question": "who directed X?"})
    assert out["route"] == "graph"
    assert "multi-hop" in out["route_reason"]


def test_supervisor_falls_back_on_llm_failure(monkeypatch):
    monkeypatch.setattr(G, "get_llm", lambda: make_llm(raise_on_structured=True))
    out = G.supervisor_node({"redacted_question": "what is X?"})
    assert out["route"] in {"graph", "vector", "both"}
    assert "fallback" in out["route_reason"]


def test_supervisor_repair_forces_both(monkeypatch):
    # on a retry it must NOT call the LLM; it broadens to both
    monkeypatch.setattr(
        G, "get_llm", lambda: (_ for _ in ()).throw(AssertionError("LLM must not be called"))
    )
    out = G.supervisor_node({"redacted_question": "q", "retries": 1})
    assert out["route"] == "both"


# --- synthesis --------------------------------------------------------------
def test_synthesis_extracts_citations(monkeypatch):
    monkeypatch.setattr(
        G, "get_llm", lambda: make_llm(answer="Directed by A [Nemesis 2] and made by [Studio].")
    )
    out = G.synthesis_node({"redacted_question": "q", "vector_context": "ctx"})
    assert out["citations"] == ["Nemesis 2", "Studio"]
    assert out["answer"].startswith("Directed by A")


# --- grader -----------------------------------------------------------------
def test_grader_empty_answer_is_ungrounded():
    out = G.grader_node({"redacted_question": "q", "answer": ""})
    assert out["grounded"] is False


def test_grader_uses_llm_verdict(monkeypatch):
    monkeypatch.setattr(
        G, "get_llm", lambda: make_llm(grounded=GroundingVerdict(grounded=True, reason="supported"))
    )
    out = G.grader_node({"redacted_question": "q", "answer": "A [S]", "vector_context": "A is S"})
    assert out["grounded"] is True
    assert "supported" in out["grader_reason"]


# --- repair loop control ----------------------------------------------------
def test_after_grader_ends_when_grounded():
    assert G._after_grader({"grounded": True}) == "end"


def test_after_grader_repairs_when_budget_left(monkeypatch):
    monkeypatch.setattr(G, "get_settings", lambda: SimpleNamespace(max_retries=1))
    assert G._after_grader({"grounded": False, "retries": 0}) == "repair"


def test_after_grader_ends_when_budget_exhausted(monkeypatch):
    monkeypatch.setattr(G, "get_settings", lambda: SimpleNamespace(max_retries=1))
    assert G._after_grader({"grounded": False, "retries": 1}) == "end"


def test_repair_increments_retries():
    assert G.repair_node({"retries": 0})["retries"] == 1
    assert G.repair_node({"retries": 2})["retries"] == 3


# --- _fill safety (regression on the L10 brace bug) -------------------------
def test_fill_leaves_literal_braces_untouched():
    assert G._fill("a {x} b {y}", x="{name}", y="Z") == "a {name} b Z"
