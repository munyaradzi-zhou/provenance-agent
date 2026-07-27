"""Central config. Reads from environment; never hardcode secrets."""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # Embeddings: high-volume, so a small/cheap model. Kept on the same provider
    # as the LLM for one key; dim must match the collection's vector size.
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    neo4j_uri: str = "bolt://localhost:7687"
    # Accept both NEO4J_USER and Aura's native NEO4J_USERNAME.
    neo4j_user: str = Field(
        default="neo4j", validation_alias=AliasChoices("neo4j_user", "neo4j_username")
    )
    neo4j_password: str = "password"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""  # required for Qdrant Cloud; empty for local
    qdrant_collection: str = "provenance"

    # Retrieval knobs
    top_k: int = 5
    rerank_enabled: bool = False

    # Agent orchestration
    max_retries: int = 1  # repair-loop cap: how many times to re-retrieve if ungrounded

    # API layer
    api_keys: str = ""  # comma-separated valid keys; empty = auth disabled (dev only)
    rate_limit: str = "60/minute"  # per-key limit (slowapi syntax)
    request_timeout_s: float = 30.0  # hard cap on a single /query
    cors_origins: str = "*"  # comma-separated allowed origins for the browser client

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()] or ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
