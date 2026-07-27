"""Shared LLM factory — one place to construct the chat model.

Keeps model choice (`gpt-4o-mini`), temperature, and the key in a single spot so
every agent (supervisor, synthesis, text-to-Cypher) is consistent and swappable.
temperature=0 for reproducible eval.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import get_settings


@lru_cache
def get_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(model=s.llm_model, api_key=SecretStr(s.openai_api_key), temperature=0)
