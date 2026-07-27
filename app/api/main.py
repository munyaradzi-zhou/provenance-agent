"""FastAPI service wrapping the LangGraph. Run: uvicorn app.api.main:app --reload"""

from fastapi import FastAPI
from pydantic import BaseModel

from app.agents.graph import compiled_graph

app = FastAPI(title="ProvenanceAgent", version="0.1.0")


class QueryIn(BaseModel):
    question: str


class QueryOut(BaseModel):
    answer: str
    route: str | None = None  # which retrieval strategy the supervisor chose
    grounded: bool | None = None  # grader verdict
    citations: list[str] = []  # source titles cited in the answer
    trace: list[str] = []  # full reasoning trace (route choice, grader verdict, ...)
    faithfulness: float | None = None  # RAGAS self-score (Phase 5)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/query", response_model=QueryOut)
def query(body: QueryIn) -> QueryOut:
    result = compiled_graph.invoke({"question": body.question})
    return QueryOut(
        answer=result.get("answer", ""),
        route=result.get("route"),
        grounded=result.get("grounded"),
        citations=result.get("citations", []),
        trace=result.get("trace", []),
        faithfulness=result.get("faithfulness"),
    )
