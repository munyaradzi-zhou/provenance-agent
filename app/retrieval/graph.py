"""Graph retrieval over Neo4j via LLM-generated, read-only Cypher.

Flow (with error handling built in):
  1. LLM turns the question into a Cypher query, constrained to our schema.
  2. `is_read_only` rejects anything that could mutate the graph (injection guard).
  3. Execute in a READ transaction; format rows into context.
  4. On empty result OR any failure, fall back to a deterministic
     entity-neighbourhood lookup so the graph agent still contributes something.

Schema (see docs/schema.md): (:Entity {name})-[:REL {name}]->(:Entity)
"""

from __future__ import annotations

import re
from typing import Any

from neo4j import Driver, GraphDatabase

from app.core.config import get_settings
from app.core.llm import get_llm

# Whole-word, case-insensitive write/DDL clauses that must never run here.
_WRITE_CLAUSES = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|FOREACH|LOAD|CALL)\b",
    re.IGNORECASE,
)

_SCHEMA_HINT = (
    "Graph schema: nodes are (:Entity {name}); relationships are "
    "(:Entity)-[:REL {name}]->(:Entity) where REL.name is a Wikidata relation "
    "such as 'director', 'mother', 'country of citizenship'."
)

_CYPHER_PROMPT = (
    "You translate a question into ONE read-only Cypher query.\n"
    f"{_SCHEMA_HINT}\n"
    "Rules: return ONLY the Cypher, no prose, no code fences. Use only MATCH, "
    "WHERE, RETURN, LIMIT. Never write to the graph. Always end with LIMIT 25.\n\n"
    "Question: {question}\nCypher:"
)


def is_read_only(cypher: str) -> bool:
    """True only if the query contains no write/DDL clauses and no multi-statement."""
    stripped = cypher.strip().rstrip(";")
    if ";" in stripped:  # no stacked statements
        return False
    return _WRITE_CLAUSES.search(stripped) is None


def _clean(cypher: str) -> str:
    """Strip markdown fences / stray labels the LLM might add."""
    cypher = re.sub(r"^```(?:cypher)?|```$", "", cypher.strip(), flags=re.MULTILINE)
    return cypher.strip()


class GraphRetriever:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._driver: Driver | None = None

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            s = self.settings
            self._driver = GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))
        return self._driver

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def generate_cypher(self, question: str) -> str:
        # NB: use replace, not .format — the prompt contains literal {name} braces
        # from the schema description, which str.format would misparse.
        prompt = _CYPHER_PROMPT.replace("{question}", question)
        msg = get_llm().invoke(prompt)
        return _clean(str(msg.content))

    def _run_read(self, cypher: str, **params: Any) -> list[dict]:
        with self.driver.session() as session:
            result = session.run(cypher, params)
            return [dict(r) for r in result]

    def _fallback(self, question: str) -> list[dict]:
        """Deterministic: find entities whose name appears in the question,
        return their 1-hop neighbourhood."""
        cypher = (
            "MATCH (e:Entity) WHERE toLower($q) CONTAINS toLower(e.name) "
            "MATCH (e)-[r:REL]-(n:Entity) "
            "RETURN e.name AS entity, r.name AS relation, n.name AS neighbor LIMIT 25"
        )
        return self._run_read(cypher, q=question)

    @staticmethod
    def _format(rows: list[dict]) -> str:
        return "\n".join(" | ".join(f"{k}: {v}" for k, v in row.items()) for row in rows)

    def retrieve(self, question: str) -> str:
        # 1. try LLM-generated Cypher, guarded
        try:
            cypher = self.generate_cypher(question)
            if is_read_only(cypher):
                rows = self._run_read(cypher)
                if rows:
                    return self._format(rows)
        except Exception:  # noqa: BLE001 - any failure falls through to fallback
            pass
        # 2. deterministic fallback
        try:
            rows = self._fallback(question)
            return self._format(rows)
        except Exception:  # noqa: BLE001
            return ""
