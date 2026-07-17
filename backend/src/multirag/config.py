"""Runtime configuration loaded from environment (.env)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------- Postgres -------
    database_url: str = "postgresql://multirag:multirag@localhost:5432/multirag"

    # ------- Anthropic -------
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    anthropic_max_tokens: int = 4096
    anthropic_temperature: float = 0.0

    # ------- Embeddings -------
    # `openai`                : hosted API, needs OPENAI_API_KEY.  (default)
    # `voyage`                : hosted API, needs VOYAGE_API_KEY.
    # `sentence_transformers` : local HuggingFace model.  Requires the `local`
    #                           extra (`pip install -e ".[local]"`) which pulls torch.
    embed_provider: Literal["openai", "voyage", "sentence_transformers"] = "openai"
    embed_model: str = "text-embedding-3-large"
    embed_dimensions: int = 1024
    # Only used by the sentence-transformers path. BGE-family models expect a
    # query prefix but no document prefix; e5-family expects both. Ignored by
    # OpenAI / Voyage (those handle task-type internally).
    embed_query_prefix: str = "Represent this sentence for searching relevant passages: "
    embed_doc_prefix: str = ""
    # Only needed for their respective providers.
    openai_api_key: str = ""
    voyage_api_key: str = ""

    # ------- Pinecone -------
    pinecone_api_key: str = ""
    pinecone_index: str = "multirag-docs"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    # ------- App -------
    app_env: Literal["dev", "staging", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    chunk_size: int = Field(default=800, ge=100, le=4000)
    chunk_overlap: int = Field(default=100, ge=0, le=800)
    docs_staging_dir: str = "./docs"

    # ------- Memory -------
    # Every memory row is scoped by user_id. The demo hard-codes it here; the
    # column exists in Postgres so multi-tenant is a config change, not a
    # migration. Change to a per-request value once auth is wired.
    memory_user_id: str = "local"
    # When True, after each chat turn we fire-and-forget an Anthropic call to
    # fold the older messages into a rolling summary. Off by default to keep
    # dev API costs predictable.
    memory_auto_summarize: bool = False
    memory_recall_top_k: int = Field(default=5, ge=1, le=20)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
