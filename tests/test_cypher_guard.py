"""The read-only Cypher guard is a security boundary (text-to-Cypher injection).
These are pure-function tests — no database needed."""

import pytest
from app.retrieval.graph import _clean, is_read_only

READ_OK = [
    "MATCH (e:Entity {name: 'X'})-[:REL]->(n) RETURN n LIMIT 25",
    "match (a)-[r:REL]-(b) where a.name = 'y' return a,r,b limit 10",
]

WRITE_BLOCKED = [
    "MATCH (e:Entity) DELETE e",
    "MERGE (x:Entity {name:'evil'}) RETURN x",
    "MATCH (e) SET e.hacked = true RETURN e",
    "MATCH (e) DETACH DELETE e",
    "DROP CONSTRAINT entity_name",
    "CALL apoc.periodic.iterate('MATCH (n) RETURN n','DELETE n',{})",
    "LOAD CSV FROM 'http://evil' AS row RETURN row",
    "MATCH (n) RETURN n; DROP DATABASE neo4j",  # stacked statements
]


@pytest.mark.parametrize("q", READ_OK)
def test_read_queries_pass(q):
    assert is_read_only(q) is True


@pytest.mark.parametrize("q", WRITE_BLOCKED)
def test_write_queries_blocked(q):
    assert is_read_only(q) is False


def test_clean_strips_code_fences():
    fenced = "```cypher\nMATCH (n) RETURN n\n```"
    assert _clean(fenced) == "MATCH (n) RETURN n"


def test_prompt_preserves_literal_braces():
    """Regression: the prompt has literal {name} braces from the schema hint;
    substitution must use .replace, not str.format (which would KeyError)."""
    from app.retrieval.graph import _CYPHER_PROMPT

    prompt = _CYPHER_PROMPT.replace("{question}", "Who directed X?")
    assert "Who directed X?" in prompt
    assert "{name}" in prompt  # literal braces survive untouched
