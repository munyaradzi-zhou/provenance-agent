"""Production FastAPI service around the LangGraph.

Adds the production concerns the agent graph itself shouldn't care about:
API-key auth, per-key rate limiting, request timeouts, a consistent error
envelope, request-id + latency, structured JSON logging, CORS, and a
liveness/readiness split.

Run: uvicorn app.api.main:app --reload
"""

from __future__ import annotations

import asyncio

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.agents.graph import compiled_graph
from app.api.auth import api_key_identity, require_api_key
from app.api.errors import register_error_handlers
from app.api.observability import configure_logging, register_request_middleware
from app.api.readiness import readiness
from app.core.config import get_settings

configure_logging()

limiter = Limiter(key_func=api_key_identity)
app = FastAPI(title="ProvenanceAgent", version="1.0.0")
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_request_middleware(app)
register_error_handlers(app)


@app.exception_handler(RateLimitExceeded)
async def _rate_limited(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    rid = getattr(request.state, "request_id", "-")
    return JSONResponse(
        status_code=429,
        content={"error": {"code": 429, "message": "rate limit exceeded", "request_id": rid}},
        headers={"X-Request-ID": rid, "Retry-After": "60"},
    )


def _limit() -> str:
    return get_settings().rate_limit


class QueryIn(BaseModel):
    question: str


class QueryOut(BaseModel):
    answer: str
    route: str | None = None
    grounded: bool | None = None
    citations: list[str] = []
    trace: list[str] = []
    request_id: str
    latency_ms: float
    token_cost: float | None = None  # real cost wired via Langfuse in Phase 5
    faithfulness: float | None = None


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok"}


@app.get("/ready")
def ready() -> JSONResponse:
    """Readiness: Neo4j + Qdrant are reachable (503 if not)."""
    ok, deps = readiness()
    return JSONResponse(status_code=200 if ok else 503, content={"ready": ok, "dependencies": deps})


@app.post("/v1/query", response_model=QueryOut)
@limiter.limit(_limit)
async def query(request: Request, body: QueryIn, _key: str = Depends(require_api_key)) -> QueryOut:
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")

    rid = getattr(request.state, "request_id", "-")
    loop = asyncio.get_event_loop()
    start = loop.time()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: compiled_graph.invoke({"question": body.question})),
            timeout=get_settings().request_timeout_s,
        )
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail="request timed out") from e

    latency_ms = round((loop.time() - start) * 1000, 1)
    return QueryOut(
        answer=result.get("answer", ""),
        route=result.get("route"),
        grounded=result.get("grounded"),
        citations=result.get("citations", []),
        trace=result.get("trace", []),
        request_id=rid,
        latency_ms=latency_ms,
        faithfulness=result.get("faithfulness"),
    )
