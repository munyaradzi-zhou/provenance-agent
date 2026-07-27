"""Shared graph state passed between agents in the LangGraph.

`trace` uses an Annotated reducer so that when graph_agent and vector_agent run
in parallel (route="both"), their trace entries are merged instead of colliding.
Every other field is last-write-wins (a single node owns it).
"""

import operator
from typing import Annotated, Literal, TypedDict


class AgentState(TypedDict, total=False):
    question: str  # the user's raw question
    redacted_question: str  # after PII redaction
    route: Literal["graph", "vector", "both"]  # supervisor decision
    route_reason: str  # why the supervisor chose that route
    graph_context: str  # retrieved via Cypher
    vector_context: str  # retrieved via semantic search
    answer: str  # synthesised final answer
    citations: list[str]  # source titles cited in the answer
    grounded: bool | None  # grader verdict: is the answer supported by context?
    grader_reason: str  # grader's one-line justification
    retries: int  # repair-loop counter (bounded by settings.max_retries)
    trace: Annotated[list[str], operator.add]  # merged across parallel nodes
    faithfulness: float | None  # RAGAS self-score (wired in Phase 5)
