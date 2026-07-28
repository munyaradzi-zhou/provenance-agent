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
    # Placeholder form differs by backend: Presidio emits [EMAIL_ADDRESS] /
    # [PHONE_NUMBER]; the regex fallback emits [EMAIL] / [PHONE]. Assert the
    # PII is gone and a typed placeholder is present, regardless of backend.
    email_out = redact("mail me at a@b.com")
    assert "a@b.com" not in email_out
    assert "[EMAIL" in email_out

    phone_out = redact("call +39 371 617 1621")
    assert "371 617" not in phone_out
    assert "[PHONE" in phone_out


def test_redaction_preserves_domain_entities():
    # Film/entity questions must pass through untouched — people and places are
    # the retrieval targets in this domain, not PII to strip.
    q = "What nationality is the director of the film Nemesis 2: Nebula?"
    assert redact(q) == q


def test_redaction_financial_pii():
    # Contact/financial identifiers a user might accidentally paste get stripped
    # when Presidio is present; the regex fallback only covers email/phone, so
    # these assertions are Presidio-gated to keep the fallback-only path green.
    from app.core.redaction import _get_redactor

    if _get_redactor().__name__ != "_presidio_redact":
        return  # regex fallback: no card/IBAN coverage, nothing to assert
    assert "4111" not in redact("card 4111 1111 1111 1111")
    assert "GB82" not in redact("IBAN GB82 WEST 1234 5698 7654 32")
