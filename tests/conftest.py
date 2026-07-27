"""Shared test helpers: a FakeLLM so agent tests run offline (no API calls)."""

from types import SimpleNamespace

from app.agents.schemas import RouteDecision


class FakeLLM:
    """Stands in for ChatOpenAI. Supports both the structured-output path
    (router, grader) and the plain .invoke path (synthesis)."""

    def __init__(self, *, route=None, grounded=None, answer="", raise_on_structured=False):
        self._route = route
        self._grounded = grounded
        self._answer = answer
        self._raise = raise_on_structured

    def with_structured_output(self, model):
        if self._raise:
            raise RuntimeError("simulated router/grader failure")
        payload = self._route if model is RouteDecision else self._grounded
        return SimpleNamespace(invoke=lambda _prompt: payload)

    def invoke(self, _prompt):
        return SimpleNamespace(content=self._answer)


def make_llm(**kw) -> FakeLLM:
    return FakeLLM(**kw)
