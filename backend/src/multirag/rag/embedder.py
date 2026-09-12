"""Embedding client.

Four providers, one interface:

  - `sentence_transformers` : local HuggingFace model (default; free, no API key).
  - `openai`                : hosted API, `text-embedding-3-*`.
  - `voyage`                : hosted API, Voyage AI.
  - `openrouter`            : hosted API, any embedding model OpenRouter proxies
                              (OpenAI-compatible endpoint).

The protocol exposes separate `embed_documents` and `embed_query` calls because
some open-source retrieval models (BGE, E5) want a task-specific prefix on the
query side only. Hosted APIs ignore the prefixes (Voyage handles it internally
via `input_type`; OpenAI doesn't need one).
"""

from __future__ import annotations

from typing import Protocol

from multirag.config import get_settings
from multirag.logging import get_logger

log = get_logger(__name__)

BATCH_SIZE = 96


class EmbeddingClient(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...

    @property
    def dimensions(self) -> int: ...

    @property
    def model(self) -> str: ...


# ---------------------------------------------------------------------------
# Local (sentence-transformers) — default
# ---------------------------------------------------------------------------

class SentenceTransformerEmbedder:
    """Local HuggingFace model. First call downloads weights (~1-2 GB for bge-large)."""

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        self._model_name = settings.embed_model
        self._dim = settings.embed_dimensions
        self._query_prefix = settings.embed_query_prefix
        self._doc_prefix = settings.embed_doc_prefix

        log.info("embedder.local.loading", model=self._model_name)
        self._st = SentenceTransformer(self._model_name)
        actual_dim = int(self._st.get_sentence_embedding_dimension())
        if actual_dim != self._dim:
            log.warning(
                "embedder.dim_mismatch",
                configured_dim=self._dim,
                model_dim=actual_dim,
                hint=("Set EMBED_DIMENSIONS to match the model's native dim, "
                      "then recreate the Pinecone index."),
            )
            self._dim = actual_dim

    @property
    def dimensions(self) -> int:
        return self._dim

    @property
    def model(self) -> str:
        return self._model_name

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vecs = self._st.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return [v.tolist() for v in vecs]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._doc_prefix:
            texts = [self._doc_prefix + t for t in texts]
        return self._encode(texts)

    def embed_query(self, text: str) -> list[float]:
        prefixed = (self._query_prefix + text) if self._query_prefix else text
        return self._encode([prefixed])[0]


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class OpenAIEmbedder:
    def __init__(self) -> None:
        from openai import OpenAI

        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model_name = settings.embed_model
        self._dim = settings.embed_dimensions

    @property
    def dimensions(self) -> int:
        return self._dim

    @property
    def model(self) -> str:
        return self._model_name

    def _call(self, batch: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(
            model=self._model_name,
            input=batch,
            dimensions=self._dim,
        )
        return [e.embedding for e in resp.data]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for batch in _batches(texts, BATCH_SIZE):
            out.extend(self._call(batch))
        return out

    def embed_query(self, text: str) -> list[float]:
        return self._call([text])[0]


# ---------------------------------------------------------------------------
# Voyage AI
# ---------------------------------------------------------------------------

class VoyageEmbedder:
    def __init__(self) -> None:
        try:
            import voyageai
        except ImportError as e:
            raise RuntimeError("voyageai package not installed") from e

        settings = get_settings()
        if not settings.voyage_api_key:
            raise RuntimeError("VOYAGE_API_KEY is not set")
        self._client = voyageai.Client(api_key=settings.voyage_api_key)
        self._model_name = (
            settings.embed_model if settings.embed_model.startswith("voyage") else "voyage-3"
        )
        self._dim = settings.embed_dimensions

    @property
    def dimensions(self) -> int:
        return self._dim

    @property
    def model(self) -> str:
        return self._model_name

    def _call(self, batch: list[str], input_type: str) -> list[list[float]]:
        r = self._client.embed(batch, model=self._model_name, input_type=input_type)
        return r.embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for batch in _batches(texts, BATCH_SIZE):
            out.extend(self._call(batch, "document"))
        return out

    def embed_query(self, text: str) -> list[float]:
        return self._call([text], "query")[0]


# ---------------------------------------------------------------------------
# OpenRouter
# ---------------------------------------------------------------------------

class OpenRouterEmbedder:
    """Hosted embeddings via OpenRouter's OpenAI-compatible `/embeddings`.

    Uses the OpenAI SDK against a custom base_url, so any embedding model
    OpenRouter proxies works by setting EMBED_MODEL. Free-tier models (e.g.
    `liquid/lfm-2.5-embedding-350m:free`) need no OpenAI key. Note: some models
    reject a `dimensions` argument, so it's only sent when the model supports
    truncation — set EMBED_DIMENSIONS to the model's native output.
    """

    def __init__(self) -> None:
        from openai import OpenAI

        settings = get_settings()
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        self._client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
        self._model_name = settings.embed_model
        self._dim = settings.embed_dimensions

    @property
    def dimensions(self) -> int:
        return self._dim

    @property
    def model(self) -> str:
        return self._model_name

    def _call(self, batch: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._model_name, input=batch)
        return [e.embedding for e in resp.data]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for batch in _batches(texts, BATCH_SIZE):
            out.extend(self._call(batch))
        return out

    def embed_query(self, text: str) -> list[float]:
        return self._call([text])[0]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def _batches(items: list[str], n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


_embedder: EmbeddingClient | None = None


def get_embedder() -> EmbeddingClient:
    global _embedder
    if _embedder is not None:
        return _embedder
    settings = get_settings()
    if settings.embed_provider == "sentence_transformers":
        _embedder = SentenceTransformerEmbedder()
    elif settings.embed_provider == "openai":
        _embedder = OpenAIEmbedder()
    elif settings.embed_provider == "voyage":
        _embedder = VoyageEmbedder()
    elif settings.embed_provider == "openrouter":
        _embedder = OpenRouterEmbedder()
    else:
        raise ValueError(f"unknown embed_provider '{settings.embed_provider}'")
    log.info(
        "embedder.ready",
        provider=settings.embed_provider,
        model=_embedder.model,
        dim=_embedder.dimensions,
    )
    return _embedder
