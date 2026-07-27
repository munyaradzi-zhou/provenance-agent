"""Langfuse tracing (v4). One place to init the client + hand out a LangChain
callback handler that captures the full graph run — every node, LLM call, token
count, latency, and cost — and ships it to Langfuse.

Tracing is best-effort: if keys aren't configured, everything no-ops so the app
runs fine locally without Langfuse.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.core.config import get_settings

log = logging.getLogger("provenance.tracing")


@lru_cache
def _client() -> Any | None:
    """Initialise the global Langfuse client once (or None if not configured)."""
    s = get_settings()
    if not (s.langfuse_public_key and s.langfuse_secret_key):
        return None
    try:
        from langfuse import Langfuse

        return Langfuse(
            public_key=s.langfuse_public_key,
            secret_key=s.langfuse_secret_key,
            host=s.langfuse_host,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("langfuse init failed (%s); tracing disabled", type(e).__name__)
        return None


def tracing_enabled() -> bool:
    return _client() is not None


def get_callback_handler() -> Any | None:
    """A LangChain CallbackHandler bound to the global client, or None."""
    if _client() is None:
        return None
    from langfuse.langchain import CallbackHandler

    return CallbackHandler()


def flush() -> None:
    """Force-send buffered traces (call at the end of short-lived scripts)."""
    c = _client()
    if c is not None:
        c.flush()
