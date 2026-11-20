"""Legal agent: LegalMind's tools over MCP, mocked so the tests run offline."""

import asyncio
import json
from types import SimpleNamespace

import app.agents.graph as G
import app.agents.legal as L
from app.agents.schemas import GroundingVerdict, RouteDecision
from app.core.config import get_settings

from tests.conftest import make_llm

SEARCH_RESULT = json.dumps(
    [
        {
            "title": "Huurovereenkomst woonruimte Lindenlaan 14-2 Utrecht",
            "page": 1,
            "content": "Huurder betaalt bij het aangaan een waarborgsom van € 2.370,00.",
        }
    ]
)


class FakeTool:
    def __init__(self, name, result):
        self.name = name
        self.result = result
        self.calls = []

    async def ainvoke(self, args):
        self.calls.append(args)
        return self.result


class FakeToolLLM:
    """bind_tools() -> replies with the scripted tool calls, then with no calls."""

    def __init__(self, scripted):
        self.scripted = list(scripted)

    def bind_tools(self, tools):
        self.tools = tools
        return self

    async def ainvoke(self, _messages):
        calls = self.scripted.pop(0) if self.scripted else []
        return SimpleNamespace(tool_calls=calls, content="DONE")


def _configure(monkeypatch, *, url="https://mcp.example/mcp", key="k"):
    monkeypatch.setattr(get_settings(), "legalmind_mcp_url", url)
    monkeypatch.setattr(get_settings(), "legalmind_mcp_api_key", key)


def test_legal_route_needs_configuration(monkeypatch):
    _configure(monkeypatch, url="", key="")
    monkeypatch.setattr(
        G, "get_llm", lambda: make_llm(route=RouteDecision(route="legal", reason="Dutch law"))
    )
    out = G.supervisor_node({"redacted_question": "Wat is de opzegtermijn?"})
    assert out["route"] == "both"  # no LegalMind configured: fall back to the local stores


def test_agent_discovers_and_calls_tools(monkeypatch):
    _configure(monkeypatch)
    search = FakeTool("search_legal_documents", SEARCH_RESULT)
    tools = [search, FakeTool("ask_legal_question", "{}"), FakeTool("list_agents", "[]")]
    monkeypatch.setattr(L, "_client", lambda: SimpleNamespace(get_tools=lambda: _async(tools)))
    llm = FakeToolLLM(
        [[{"name": "search_legal_documents", "args": {"query": "waarborgsom"}, "id": "c1"}]]
    )
    monkeypatch.setattr(L, "get_llm", lambda: llm)

    result = L.run_legal_agent("Hoe hoog is de waarborgsom?")

    assert result.tools_discovered == [
        "ask_legal_question",
        "list_agents",
        "search_legal_documents",
    ]
    assert search.calls == [{"query": "waarborgsom"}]
    assert "[Huurovereenkomst woonruimte Lindenlaan 14-2 Utrecht, p. 1]" in result.context
    assert "2.370,00" in result.context
    assert any("MCP call search_legal_documents" in line for line in result.trace)


def test_tool_call_budget_is_enforced(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(get_settings(), "legal_max_tool_calls", 2)
    search = FakeTool("search_legal_documents", SEARCH_RESULT)
    monkeypatch.setattr(L, "_client", lambda: SimpleNamespace(get_tools=lambda: _async([search])))
    call = {"name": "search_legal_documents", "args": {"query": "x"}, "id": "c"}
    monkeypatch.setattr(L, "get_llm", lambda: FakeToolLLM([[call, call], [call], [call]]))

    result = L.run_legal_agent("?")

    assert len(result.tool_calls) == 2


def test_graph_answers_through_the_legal_route(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(
        G,
        "get_llm",
        lambda: make_llm(
            route=RouteDecision(route="legal", reason="Dutch tenancy contract"),
            answer="De waarborgsom is € 2.370,00 [Huurovereenkomst woonruimte Lindenlaan 14-2 Utrecht, p. 1].",
            grounded=GroundingVerdict(grounded=True, reason="supported"),
        ),
    )
    monkeypatch.setattr(
        G,
        "run_legal_agent",
        lambda q: L.LegalResult(
            context=L._as_context("search_legal_documents", SEARCH_RESULT),
            tool_calls=[{"tool": "search_legal_documents", "args": {"query": q}}],
            trace=["legal agent: MCP call search_legal_documents(...)"],
        ),
    )

    result = G.compiled_graph.invoke({"question": "Hoe hoog is de waarborgsom?"})

    assert result["route"] == "legal"
    assert result["grounded"] is True
    assert result["tool_calls"][0]["tool"] == "search_legal_documents"
    assert "2.370,00" in result["legal_context"]
    assert "graph_context" not in result and "vector_context" not in result


def test_ask_result_keeps_legalminds_grounding_label():
    raw = json.dumps(
        {
            "answer": "Eén maand.",
            "grounding": "documents",
            "citations": [
                {"title": "Arbeidsovereenkomst", "page": 1, "excerpt": "proeftijd van één maand"}
            ],
        }
    )
    context = L._as_context("ask_legal_question", raw)
    assert "grounding check: documents" in context
    assert "[Arbeidsovereenkomst, p. 1] proeftijd van één maand" in context


async def _coro(value):
    return value


def _async(value):
    return _coro(value)


def test_helpers_run():  # keep the coroutine helper honest
    assert asyncio.run(_coro(1)) == 1


def test_azure_openai_provider_uses_entra_id(monkeypatch):
    import app.core.llm as llm_module
    from langchain_openai import AzureChatOpenAI

    s = get_settings()
    monkeypatch.setattr(s, "llm_provider", "azure_openai")
    monkeypatch.setattr(s, "azure_openai_endpoint", "https://oai.example.openai.azure.com/")
    monkeypatch.setattr(s, "azure_openai_deployment", "gpt-4.1-mini")
    llm_module.get_llm.cache_clear()
    try:
        llm = llm_module.get_llm()
        assert isinstance(llm, AzureChatOpenAI)
        assert llm.deployment_name == "gpt-4.1-mini"
        assert llm.openai_api_key is None  # a token provider, no key
    finally:
        llm_module.get_llm.cache_clear()
