"""Load triples.jsonl into Neo4j as an (:Entity)-[:REL {name}]->(:Entity) graph.

Idempotent: uses MERGE + a uniqueness constraint, so re-running never duplicates.
Batched via UNWIND for speed.

Usage:  python -m app.ingest.build_graph
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

from neo4j import GraphDatabase

from app.core.config import get_settings

TRIPLES = pathlib.Path("data/processed/triples.jsonl")
BATCH = 500

_CONSTRAINT = """
CREATE CONSTRAINT entity_name IF NOT EXISTS
FOR (e:Entity) REQUIRE e.name IS UNIQUE
"""

# One batch of triples -> nodes + a generic REL edge carrying the relation name.
_UPSERT = """
UNWIND $rows AS row
MERGE (s:Entity {name: row.subject})
MERGE (o:Entity {name: row.object})
MERGE (s)-[r:REL {name: row.relation}]->(o)
"""


def _load_triples() -> list[dict[str, Any]]:
    if not TRIPLES.exists():
        raise SystemExit(f"{TRIPLES} not found. Run `python -m app.ingest.subset` first.")
    return [
        json.loads(line)
        for line in TRIPLES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build() -> int:
    s = get_settings()
    rows = _load_triples()
    driver = GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))
    try:
        with driver.session() as session:
            session.run(_CONSTRAINT)
            for i in range(0, len(rows), BATCH):
                session.run(_UPSERT, rows=rows[i : i + BATCH])
        with driver.session() as session:
            node_rec = session.run("MATCH (e:Entity) RETURN count(e) AS c").single()
            edge_rec = session.run("MATCH ()-[r:REL]->() RETURN count(r) AS c").single()
            n_nodes = node_rec["c"] if node_rec else 0
            n_edges = edge_rec["c"] if edge_rec else 0
    finally:
        driver.close()
    print(f"Neo4j: {n_nodes} entities, {n_edges} relations from {len(rows)} triples.")
    return n_nodes


if __name__ == "__main__":
    build()
