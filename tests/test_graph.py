"""Smoke test: the graph runs end-to-end and redaction works."""

from app.agents.graph import compiled_graph
from app.core.redaction import redact


def test_graph_runs():
    result = compiled_graph.invoke({"question": "What produced result X?"})
    assert result["answer"]
    assert isinstance(result["trace"], list)
    assert len(result["trace"]) >= 3


def test_redaction():
    assert "[EMAIL]" in redact("mail me at a@b.com")
    assert "[PHONE]" in redact("call +39 371 617 1621")
