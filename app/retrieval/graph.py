"""Graph retrieval over Neo4j. Week 1-2: wire real Cypher generation."""

from app.core.config import get_settings


class GraphRetriever:
    def __init__(self) -> None:
        self.settings = get_settings()
        # TODO(week1): init neo4j driver
        #   from neo4j import GraphDatabase
        #   self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def retrieve(self, question: str) -> str:
        """Generate Cypher from the question, run it, return context.

        TODO(week1): use an LLM to generate Cypher, execute, format results.
        For now returns a stub so the graph is runnable end-to-end.
        """
        return f"[graph-context stub for: {question}]"
