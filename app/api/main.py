"""FastAPI service wrapping the LangGraph. Run: uvicorn app.api.main:app --reload"""

from fastapi import FastAPI
from pydantic import BaseModel

from app.agents.graph import compiled_graph

app = FastAPI(title="ProvenanceAgent", version="0.1.0")


class QueryIn(BaseModel):
    question: str


class QueryOut(BaseModel):
    answer: str
    trace: list[str]
    faithfulness: float | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/query", response_model=QueryOut)
def query(body: QueryIn) -> QueryOut:
    result = compiled_graph.invoke({"question": body.question})
    return QueryOut(
        answer=result.get("answer", ""),
        trace=result.get("trace", []),
        faithfulness=result.get("faithfulness"),
    )
