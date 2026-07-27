"""Central config. Reads from environment; never hardcode secrets."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # Embeddings: high-volume, so a small/cheap model. Kept on the same provider
    # as the LLM for one key; dim must match the collection's vector size.
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "provenance"

    # Retrieval knobs
    top_k: int = 5
    rerank_enabled: bool = False

    # Agent orchestration
    max_retries: int = 1  # repair-loop cap: how many times to re-retrieve if ungrounded

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
