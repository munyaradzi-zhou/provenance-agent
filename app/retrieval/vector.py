"""Vector retrieval over Qdrant: embed the question, ANN search, format context.

Optional hybrid re-ranking (`rerank_enabled`): over-fetch candidates, then boost
by lexical overlap with the question before truncating to top_k. A cheap,
dependency-free way to combine semantic similarity with keyword signal.
"""

from __future__ import annotations

import re

from qdrant_client import QdrantClient

from app.core.config import get_settings
from app.retrieval.embeddings import embed_query

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


class VectorRetriever:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: QdrantClient | None = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                url=self.settings.qdrant_url,
                api_key=self.settings.qdrant_api_key or None,
                timeout=60,
            )
        return self._client

    def search(self, question: str, k: int | None = None) -> list[dict]:
        """Return up to k hits: {title, text, score}."""
        k = k or self.settings.top_k
        fetch = k * 3 if self.settings.rerank_enabled else k
        vector = embed_query(question)
        hits = self.client.query_points(
            collection_name=self.settings.qdrant_collection,
            query=vector,
            limit=fetch,
            with_payload=True,
        ).points

        results = [
            {
                "title": (h.payload or {}).get("title", ""),
                "text": (h.payload or {}).get("text", ""),
                "score": h.score,
            }
            for h in hits
        ]

        if self.settings.rerank_enabled:
            q_tokens = _tokens(question)
            for r in results:
                overlap = len(q_tokens & _tokens(r["title"] + " " + r["text"]))
                r["score"] = r["score"] + 0.05 * overlap  # small lexical boost
            results.sort(key=lambda r: r["score"], reverse=True)

        return results[:k]

    def retrieve(self, question: str, k: int | None = None) -> str:
        """Concatenated context string for the synthesis agent."""
        hits = self.search(question, k)
        if not hits:
            return ""
        return "\n\n".join(f"[{h['title']}] {h['text']}" for h in hits)
