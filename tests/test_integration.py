"""End-to-end retrieval against real Neo4j + Qdrant.

Marked `integration` and auto-skipped unless the services are reachable and
OPENAI_API_KEY is set. Run with services up:  pytest -m integration
Assumes the corpus has been seeded (`python -m app.ingest`).
"""

import socket

import pytest
from app.core.config import get_settings

pytestmark = pytest.mark.integration


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(scope="module")
def require_services():
    s = get_settings()
    if not s.openai_api_key:
        pytest.skip("OPENAI_API_KEY not set")
    if not _port_open("localhost", 6333):
        pytest.skip("Qdrant not reachable on :6333")
    if not _port_open("localhost", 7687):
        pytest.skip("Neo4j not reachable on :7687")


def test_vector_retrieval_returns_context(require_services):
    from app.retrieval.vector import VectorRetriever

    ctx = VectorRetriever().retrieve("Who directed Nemesis 2: Nebula?")
    assert isinstance(ctx, str) and len(ctx) > 0


def test_graph_retrieval_returns_context(require_services):
    from app.retrieval.graph import GraphRetriever

    r = GraphRetriever()
    try:
        ctx = r.retrieve("Who is the director of Nemesis 2: Nebula?")
        assert isinstance(ctx, str)
    finally:
        r.close()
