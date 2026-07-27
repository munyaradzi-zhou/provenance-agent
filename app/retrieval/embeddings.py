"""Embedding helper — one place both ingestion and retrieval get vectors from.

Uses OpenAI `text-embedding-3-small` by default (cheap, 1536-dim). Isolated here
so the provider can be swapped (local model, Cohere, ...) without touching the
ingest or retrieval code.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from app.core.config import get_settings


@lru_cache
def get_embedder() -> OpenAIEmbeddings:
    s = get_settings()
    return OpenAIEmbeddings(model=s.embedding_model, api_key=SecretStr(s.openai_api_key))


def embed_query(text: str) -> list[float]:
    return get_embedder().embed_query(text)


def embed_documents(texts: list[str]) -> list[list[float]]:
    return get_embedder().embed_documents(texts)
