"""Structured JSON logging + a request middleware.

One JSON line per request (request_id, method, path, status, latency_ms) — the
shape CloudWatch/Log-Insights can query directly in Phase 4/5. Each request gets
a UUID, echoed back in the `X-Request-ID` header so clients can correlate.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # merge any structured extras attached via logger.info(..., extra={...})
        for key in ("request_id", "method", "path", "status", "latency_ms", "route", "grounded"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    # Quiet chatty third-party loggers (one line per OpenAI/HTTP call is noise).
    for noisy in ("httpx", "httpcore", "urllib3", "openai", "neo4j"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def register_request_middleware(app: FastAPI) -> None:
    access_log = logging.getLogger("provenance.access")

    @app.middleware("http")
    async def _observe(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = rid
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        response.headers["X-Request-ID"] = rid
        access_log.info(
            "request",
            extra={
                "request_id": rid,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response
