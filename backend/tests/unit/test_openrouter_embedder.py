"""OpenRouter embedder provider."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from multirag.config import get_settings
from multirag.rag import embedder as embedder_module
from multirag.rag.embedder import OpenRouterEmbedder, get_embedder


def _settings(**over):
    s = get_settings()
    for k, v in over.items():
        object.__setattr__(s, k, v)
    return s


def _fake_embeddings_response(dim: int, n: int):
    return SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.1] * dim) for _ in range(n)],
    )


@pytest.fixture(autouse=True)
def _reset_embedder_singleton():
    embedder_module._embedder = None
    yield
    embedder_module._embedder = None


def test_missing_key_raises():
    s = _settings(openrouter_api_key="")
    with (
        patch("multirag.rag.embedder.get_settings", return_value=s),
        pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"),
    ):
        OpenRouterEmbedder()


def test_uses_openrouter_base_url_and_model():
    s = _settings(
        openrouter_api_key="sk-or-test",
        openrouter_base_url="https://openrouter.ai/api/v1",
        embed_model="liquid/lfm-2.5-embedding-350m:free",
        embed_dimensions=1024,
    )
    with (
        patch("multirag.rag.embedder.get_settings", return_value=s),
        patch("openai.OpenAI") as mock_openai,
    ):
        client = MagicMock()
        client.embeddings.create.return_value = _fake_embeddings_response(1024, 1)
        mock_openai.return_value = client

        e = OpenRouterEmbedder()
        vec = e.embed_query("hello")

    mock_openai.assert_called_once_with(
        api_key="sk-or-test", base_url="https://openrouter.ai/api/v1"
    )
    client.embeddings.create.assert_called_once_with(
        model="liquid/lfm-2.5-embedding-350m:free", input=["hello"]
    )
    assert len(vec) == 1024
    assert e.dimensions == 1024
    assert e.model == "liquid/lfm-2.5-embedding-350m:free"


def test_does_not_send_dimensions_param():
    # Some OpenRouter models reject a `dimensions` argument; it must be omitted.
    s = _settings(openrouter_api_key="k", embed_dimensions=1024)
    with (
        patch("multirag.rag.embedder.get_settings", return_value=s),
        patch("openai.OpenAI") as mock_openai,
    ):
        client = MagicMock()
        client.embeddings.create.return_value = _fake_embeddings_response(1024, 1)
        mock_openai.return_value = client
        OpenRouterEmbedder().embed_query("x")
    _, kwargs = client.embeddings.create.call_args
    assert "dimensions" not in kwargs


def test_embed_documents_batches():
    s = _settings(openrouter_api_key="k", embed_dimensions=1024)
    with (
        patch("multirag.rag.embedder.get_settings", return_value=s),
        patch("openai.OpenAI") as mock_openai,
    ):
        client = MagicMock()
        client.embeddings.create.side_effect = (
            lambda model, input: _fake_embeddings_response(1024, len(input))
        )
        mock_openai.return_value = client
        e = OpenRouterEmbedder()
        out = e.embed_documents(["a", "b", "c"])
    assert len(out) == 3
    assert all(len(v) == 1024 for v in out)


def test_factory_selects_openrouter():
    s = _settings(
        embed_provider="openrouter",
        openrouter_api_key="k",
        embed_dimensions=1024,
    )
    with (
        patch("multirag.rag.embedder.get_settings", return_value=s),
        patch("openai.OpenAI"),
    ):
        e = get_embedder()
    assert isinstance(e, OpenRouterEmbedder)
