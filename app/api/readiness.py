"""Dependency readiness checks for /ready.

Liveness (/health) says "the process is up". Readiness (/ready) says "the process
can actually serve" — i.e. Neo4j and Qdrant are reachable. Load balancers should
route on readiness, not liveness. Checks use short timeouts so /ready stays fast
even when a dependency is down.
"""

from __future__ import annotations

from qdrant_client import QdrantClient

from app.core.config import get_settings


def _check_qdrant() -> bool:
    try:
        QdrantClient(url=get_settings().qdrant_url, timeout=2).get_collections()
        return True
    except Exception:  # noqa: BLE001
        return False


def _check_neo4j() -> bool:
    from neo4j import GraphDatabase

    s = get_settings()
    driver = None
    try:
        driver = GraphDatabase.driver(
            s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password), connection_timeout=2
        )
        driver.verify_connectivity()
        return True
    except Exception:  # noqa: BLE001
        return False
    finally:
        if driver is not None:
            driver.close()


def readiness() -> tuple[bool, dict[str, str]]:
    """Return (all_ok, {dependency: 'ok'|'down'})."""
    checks = {"neo4j": _check_neo4j(), "qdrant": _check_qdrant()}
    status = {name: ("ok" if ok else "down") for name, ok in checks.items()}
    return all(checks.values()), status
