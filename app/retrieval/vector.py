"""Vector retrieval over Qdrant. Week 1-2: wire real embedding + search."""

from app.core.config import get_settings


class VectorRetriever:
    def __init__(self) -> None:
        self.settings = get_settings()
        # TODO(week1): init qdrant client + embedding model

    def retrieve(self, question: str, k: int = 4) -> str:
        """Embed the question, search top-k, return concatenated context.

        TODO(week1): real embedding + qdrant search + optional re-ranking.
        """
        return f"[vector-context stub for: {question}]"
