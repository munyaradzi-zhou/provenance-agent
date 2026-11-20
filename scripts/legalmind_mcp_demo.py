"""Demo: ProvenanceAgent answers Dutch-law questions with LegalMind's tools over MCP.

Two independent systems:
- ProvenanceAgent: LangGraph agents (this repo), OpenAI models.
- LegalMind: Semantic Kernel agents over Azure AI Search on Azure Container Apps,
  exposing its tools as a remote MCP server (github.com/munyaradzi-zhou/LegalMind-AI).

ProvenanceAgent discovers LegalMind's tools at run time, its LLM decides which to
call, and its own synthesis and grader produce and check the answer.

    export LEGALMIND_MCP_URL=https://ca-legalmind-mcp-dev.<env>.azurecontainerapps.io/mcp
    export LEGALMIND_MCP_API_KEY=...   # az keyvault secret show --vault-name <vault> -n mcp-api-key
    python -m scripts.legalmind_mcp_demo
    python -m scripts.legalmind_mcp_demo "Hoe lang is de proeftijd van Eva Kramer?" --json demo.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time

QUESTIONS = [
    "Welke opzegtermijn moet een huurder van woonruimte volgens de wet in acht nemen?",
    "Hoe hoog is de huurachterstand van mevrouw De Wit volgens het overzicht van 2 april 2026?",
    "Waarom heeft Zekerheid Schadeverzekeringen de stormclaim van de heer Visser afgewezen?",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("questions", nargs="*", default=QUESTIONS)
    parser.add_argument("--json", help="also write the full results to this file")
    args = parser.parse_args()

    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass

    from app.agents.graph import compiled_graph
    from app.agents.legal import legal_enabled

    if not legal_enabled():
        sys.exit("Set LEGALMIND_MCP_URL and LEGALMIND_MCP_API_KEY first.")

    results = []
    for question in args.questions:
        started = time.monotonic()
        state = compiled_graph.invoke({"question": question})
        seconds = time.monotonic() - started
        results.append(
            {
                "question": question,
                "seconds": round(seconds, 1),
                **{
                    k: state.get(k)
                    for k in (
                        "route",
                        "route_reason",
                        "tool_calls",
                        "answer",
                        "citations",
                        "grounded",
                        "grader_reason",
                        "trace",
                    )
                },
            }
        )

        print("=" * 100)
        print(f"Q: {question}")
        print(f"route: {state.get('route')}  ({state.get('route_reason')})")
        for line in state.get("trace", []):
            if line.startswith("legal agent"):
                print(f"  {line}")
        print(f"A: {state.get('answer')}")
        print(f"grounded: {state.get('grounded')}  ({state.get('grader_reason')})   {seconds:.1f}s")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
