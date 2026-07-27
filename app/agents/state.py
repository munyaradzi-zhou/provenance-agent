"""Shared graph state passed between agents in the LangGraph.

`trace` uses an Annotated reducer so that when graph_agent and vector_agent run
in parallel (route="both"), their trace entries are merged instead of colliding.
"""
import operator
from typing import Annotated, Literal, TypedDict


class AgentState(TypedDict, total=False):
    question: str                  # the user's raw question
    redacted_question: str         # after PII redaction
    route: Literal["graph", "vector", "both"]  # supervisor decision
    graph_context: str             # retrieved via Cypher
    vector_context: str            # retrieved via semantic search
    answer: str                    # synthesised final answer
    trace: Annotated[list[str], operator.add]  # merged across parallel nodes
    faithfulness: float | None     # RAGAS-style self-score
