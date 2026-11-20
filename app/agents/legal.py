"""Legal agent: answers Dutch-law questions with tools from LegalMind, over MCP.

LegalMind (github.com/munyaradzi-zhou/LegalMind-AI) is a separate system: Semantic
Kernel agents over Azure AI Search, deployed on Azure Container Apps. It exposes its
tools as a remote MCP server. This agent knows nothing about them in advance:

1. connect to the MCP server (streamable HTTP, API key) and **discover** its tools;
2. let the LLM **choose** which tools to call and with what arguments, for at most
   ``legal_max_tool_calls`` calls;
3. turn what the tools returned into context for ProvenanceAgent's own synthesis and
   grader, so an answer built from a remote system is checked like any other.

Every discovered tool and every call goes into the trace, so the API response shows
exactly what crossed the boundary.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.agents.prompts import load_prompt
from app.core.config import get_settings
from app.core.llm import get_llm


@dataclass
class LegalResult:
    context: str = ""
    tools_discovered: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)


def legal_enabled() -> bool:
    s = get_settings()
    return bool(s.legalmind_mcp_url and s.legalmind_mcp_api_key)


def _client() -> MultiServerMCPClient:
    s = get_settings()
    return MultiServerMCPClient(
        {
            "legalmind": {
                "transport": "streamable_http",
                "url": s.legalmind_mcp_url,
                "headers": {"Authorization": f"Bearer {s.legalmind_mcp_api_key}"},
            }
        }
    )


def _text(result: Any) -> str:
    """MCP tool results arrive as text blocks (JSON from LegalMind); join them."""
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        parts = [item.get("text", "") if isinstance(item, dict) else str(item) for item in result]
        return "\n".join(p for p in parts if p)
    return str(result)


def _as_context(tool: str, raw: str) -> str:
    """Render a LegalMind tool result as context with [title, p. N] source labels."""
    try:
        data = json.loads(raw)
    except ValueError:
        return f"[LegalMind {tool}] {raw}"
    if tool == "search_legal_documents":
        rows = data if isinstance(data, list) else [data]
        return "\n\n".join(
            f"[{r.get('title')}, p. {r.get('page')}] {r.get('content', '')}"
            for r in rows
            if isinstance(r, dict)
        )
    if tool == "ask_legal_question" and isinstance(data, dict):
        sources = "\n".join(
            f"[{c.get('title')}, p. {c.get('page')}] {c.get('excerpt', '')}"
            for c in data.get("citations", [])
        )
        return (
            f"LegalMind answer (its own grounding check: {data.get('grounding')}):\n"
            f"{data.get('answer', '')}\n\nSources it cited:\n{sources}"
        )
    return f"[LegalMind {tool}] {raw}"


async def _run(question: str) -> LegalResult:
    out = LegalResult()
    tools: list[BaseTool] = await _client().get_tools()
    by_name = {t.name: t for t in tools}
    out.tools_discovered = sorted(by_name)
    out.trace.append(f"legal agent: discovered {len(tools)} MCP tools {out.tools_discovered}")

    llm = get_llm().bind_tools(tools)
    messages: list[BaseMessage] = [
        SystemMessage(load_prompt("legal_agent")),
        HumanMessage(question),
    ]
    contexts: list[str] = []
    budget = get_settings().legal_max_tool_calls

    while budget > 0:
        reply = await llm.ainvoke(messages)
        messages.append(reply)
        calls = getattr(reply, "tool_calls", None) or []
        if not calls:
            break
        for call in calls[:budget]:
            budget -= 1
            name, args = call["name"], call.get("args", {})
            tool = by_name.get(name)
            raw = f"unknown tool {name}" if tool is None else _text(await tool.ainvoke(args))
            out.tool_calls.append({"tool": name, "args": args})
            out.trace.append(
                f"legal agent: MCP call {name}({json.dumps(args, ensure_ascii=False)})"
            )
            contexts.append(_as_context(name, raw))
            messages.append(ToolMessage(content=raw, tool_call_id=call["id"]))

    out.context = "\n\n".join(c for c in contexts if c)
    out.trace.append(
        f"legal agent: {len(out.tool_calls)} tool calls, {len(out.context)} characters of context"
    )
    return out


def run_legal_agent(question: str) -> LegalResult:
    """Synchronous entry point for the LangGraph node (the graph runs in a worker thread)."""
    return asyncio.run(_run(question))
