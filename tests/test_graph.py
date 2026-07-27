"""Smoke test: the full graph runs end-to-end (LLM mocked) and redaction works."""

import app.agents.graph as G
from app.agents.schemas import GroundingVerdict, RouteDecision
from app.core.redaction import redact

from tests.conftest import make_llm


def test_graph_runs(monkeypatch):
    # Mock the LLM so the whole graph runs offline. Retrievers fail with no
    # services and degrade to empty context, exercising the resilience paths.
    monkeypatch.setattr(
        G,
        "get_llm",
        lambda: make_llm(
            route=RouteDecision(route="vector", reason="semantic lookup"),
            answer="Albert Pyun directed it [Nemesis 2].",
            grounded=GroundingVerdict(grounded=True, reason="supported"),
        ),
    )
    result = G.compiled_graph.invoke({"question": "What produced result X?"})
    assert result["answer"]
    assert result["route"] == "vector"
    assert result["grounded"] is True
    assert isinstance(result["trace"], list) and len(result["trace"]) >= 4


def test_redaction():
    assert "[EMAIL]" in redact("mail me at a@b.com")
    assert "[PHONE]" in redact("call +39 371 617 1621")
