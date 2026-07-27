"""Pydantic schemas for the LLM nodes' structured outputs.

Using `.with_structured_output(Model)` forces the model to return valid, typed
JSON instead of free text we'd have to parse — the difference between a reliable
agent and a brittle one.
"""

from typing import Literal

from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    """Supervisor's choice of retrieval strategy."""

    route: Literal["graph", "vector", "both"] = Field(
        description="graph = multi-hop/relational; vector = semantic/single-fact; both = unsure or needs each"
    )
    reason: str = Field(description="one short sentence justifying the choice")


class GroundingVerdict(BaseModel):
    """Grader's judgement of whether the answer is supported by the context."""

    grounded: bool = Field(
        description="true only if every claim is supported by the provided context"
    )
    reason: str = Field(description="one short sentence justifying the verdict")
