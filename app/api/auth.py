"""API-key authentication.

Keys come from `settings.api_keys` (locally from .env; in AWS from Secrets
Manager, injected as an env var). If no keys are configured we run in "dev mode"
with auth disabled — but we log a warning so it can't silently ship to prod.
"""

from __future__ import annotations

import logging

from fastapi import Header, HTTPException, Request, status

from app.core.config import get_settings

log = logging.getLogger("provenance.auth")


def api_key_identity(request: Request) -> str:
    """Rate-limit key: the caller's API key if present, else their IP.
    Attached to request.state so logging/limiting share one identity."""
    key = request.headers.get("x-api-key")
    if key:
        return f"key:{key[:8]}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


async def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    """FastAPI dependency: 401 unless a valid key is presented (when auth is on)."""
    valid = get_settings().api_key_set
    if not valid:
        log.warning("auth disabled: no API keys configured (dev mode)")
        return "dev"
    if x_api_key is None or x_api_key not in valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key
