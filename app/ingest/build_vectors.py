"""Embed passages.jsonl and upsert them into Qdrant.

Idempotent: points use a stable integer id derived from the passage id, so
re-running overwrites rather than duplicates. Embeddings are batched to keep
API calls (and cost) down.

Usage:  python -m app.ingest.build_vectors
"""

from __future__ import annotations

import json
import pathlib

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import get_settings
from app.retrieval.embeddings import embed_documents

PASSAGES = pathlib.Path("data/processed/passages.jsonl")
BATCH = 128


def _load_passages() -> list[dict]:
    if not PASSAGES.exists():
        raise SystemExit(f"{PASSAGES} not found. Run `python -m app.ingest.subset` first.")
    return [
        json.loads(line)
        for line in PASSAGES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _point_id(passage_id: str) -> int:
    """Stable 63-bit int id from the hex passage id (Qdrant wants int or uuid)."""
    return int(passage_id, 16) % (2**63)


def build() -> int:
    s = get_settings()
    passages = _load_passages()
    client = QdrantClient(url=s.qdrant_url)

    client.recreate_collection(
        collection_name=s.qdrant_collection,
        vectors_config=VectorParams(size=s.embedding_dim, distance=Distance.COSINE),
    )

    total = 0
    for i in range(0, len(passages), BATCH):
        chunk = passages[i : i + BATCH]
        vectors = embed_documents([p["text"] for p in chunk])
        points = [
            PointStruct(
                id=_point_id(p["id"]),
                vector=vec,
                payload={"passage_id": p["id"], "title": p["title"], "text": p["text"]},
            )
            for p, vec in zip(chunk, vectors, strict=True)
        ]
        client.upsert(collection_name=s.qdrant_collection, points=points)
        total += len(points)
        print(f"  upserted {total}/{len(passages)}")

    print(f"Qdrant: {total} passages in collection '{s.qdrant_collection}'.")
    return total


if __name__ == "__main__":
    build()
