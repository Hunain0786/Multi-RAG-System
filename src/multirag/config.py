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
    # `sentence_transformers` = local model, no API key, downloaded from HuggingFace.
    # Change to `openai` or `voyage` if you'd rather call a hosted API instead.
    embed_provider: Literal["sentence_transformers", "openai", "voyage"] = "sentence_transformers"
    embed_model: str = "BAAI/bge-large-en-v1.5"
    embed_dimensions: int = 1024
    # Query/document prefixes for sentence-transformers only. BGE-family models
    # expect a query prefix; e5-family models expect both. Leave blank if unsure.
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
