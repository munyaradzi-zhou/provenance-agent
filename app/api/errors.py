"""Consistent error envelope + handlers.

Every error — expected (HTTPException) or not — returns the same JSON shape,
always carrying the request_id so a caller can quote it and we can grep the logs:

    {"error": {"code": 404, "message": "...", "request_id": "..."}}
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("provenance.error")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _envelope(code: int, message: str, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
        headers={"X-Request-ID": request_id},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _envelope(exc.status_code, str(exc.detail), _request_id(request))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _envelope(422, "invalid request body", _request_id(request))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        rid = _request_id(request)
        # Log the full detail server-side; never leak internals to the caller.
        log.exception("unhandled error", extra={"request_id": rid})
        return _envelope(500, "internal server error", rid)
