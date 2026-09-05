"""Unit tests for EmbeddingService."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock

import httpx
import openai
import pytest
from openai import AsyncOpenAI, RateLimitError

from src.indexing.embeddings import EmbeddingService
from src.indexing.exceptions import (
    EmbeddingServiceError,
    RateLimitExceededError,
    TokenLimitExceededError,
)
from src.indexing.models import DocumentChunk


class MockEmbeddingItem:
    """Mock item representing a single embedding vector in an OpenAI response."""

    def __init__(self, index: int, embedding: list[float]) -> None:
        self.index = index
        self.embedding = embedding


class MockEmbeddingResponse:
    """Mock response container for OpenAI embeddings.create API."""

    def __init__(self, data: list[MockEmbeddingItem]) -> None:
        self.data = data


def make_mock_response(count: int, dim: int = 1536) -> MockEmbeddingResponse:
    """Helper to generate a mock embedding response with specified item count."""
    items = [
        MockEmbeddingItem(index=i, embedding=[0.01 * (i + 1)] * dim)
        for i in range(count)
    ]
    return MockEmbeddingResponse(data=items)


def make_rate_limit_error() -> RateLimitError:
    """Helper to construct an OpenAI RateLimitError (HTTP 429)."""
    request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    response = httpx.Response(429, request=request)
    return RateLimitError(
        message="Rate limit exceeded",
        response=response,  # type: ignore[arg-type]
        body={"error": {"message": "Rate limit exceeded"}},
    )


def make_auth_error() -> openai.AuthenticationError:
    """Helper to construct an unrecoverable OpenAI AuthError (HTTP 401)."""
    request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    response = httpx.Response(401, request=request)
    return openai.AuthenticationError(
        message="Invalid API key",
        response=response,  # type: ignore[arg-type]
        body={"error": {"message": "Invalid API key"}},
    )


@pytest.fixture
def mock_client() -> AsyncOpenAI:
    """Provide a mock AsyncOpenAI client."""
    client = MagicMock(spec=AsyncOpenAI)
    client.embeddings = MagicMock()
    client.embeddings.create = AsyncMock()
    return cast(AsyncOpenAI, client)


@pytest.fixture
def service(mock_client: AsyncOpenAI) -> EmbeddingService:
    """Provide an EmbeddingService configured with a mock client."""
    return EmbeddingService(client=mock_client, initial_delay=0.001)


@pytest.mark.asyncio
async def test_embed_texts_empty_list(
    service: EmbeddingService, mock_client: AsyncOpenAI
) -> None:
    """Verify empty input texts list returns empty result without calling API."""
    result = await service.embed_texts([])
    assert result == []
    cast(MagicMock, mock_client.embeddings.create).assert_not_called()


@pytest.mark.asyncio
async def test_embed_texts_single_batch(
    service: EmbeddingService, mock_client: AsyncOpenAI
) -> None:
    """Verify embedding generation for a single batch under max_batch_size."""
    mock_resp = make_mock_response(2)
    cast(AsyncMock, mock_client.embeddings.create).return_value = mock_resp

    texts = ["First test text", "Second test text"]
    result = await service.embed_texts(texts)

    assert len(result) == 2
    assert result[0] == [0.01] * 1536
    assert result[1] == [0.02] * 1536
    cast(AsyncMock, mock_client.embeddings.create).assert_called_once_with(
        input=texts,
        model="text-embedding-3-small",
    )


@pytest.mark.asyncio
async def test_embed_texts_multiple_batches(
    mock_client: AsyncOpenAI,
) -> None:
    """Verify input list exceeding max_batch_size is split across API calls."""
    service = EmbeddingService(
        client=mock_client,
        max_batch_size=2,
        initial_delay=0.001,
    )
    cast(AsyncMock, mock_client.embeddings.create).side_effect = [
        make_mock_response(2),
        make_mock_response(2),
        make_mock_response(1),
    ]

    texts = ["text1", "text2", "text3", "text4", "text5"]
    result = await service.embed_texts(texts)

    assert len(result) == 5
    assert cast(AsyncMock, mock_client.embeddings.create).call_count == 3


@pytest.mark.asyncio
async def test_embed_texts_exceeds_token_limit(
    service: EmbeddingService, mock_client: AsyncOpenAI
) -> None:
    """Verify TokenLimitExceededError is raised when input exceeds token limit."""
    long_text = "word " * 8500

    with pytest.raises(TokenLimitExceededError, match="exceeds maximum limit"):
        await service.embed_texts([long_text])

    cast(AsyncMock, mock_client.embeddings.create).assert_not_called()


@pytest.mark.asyncio
async def test_embed_chunks_delegation(
    service: EmbeddingService, mock_client: AsyncOpenAI
) -> None:
    """Verify embed_chunks extracts contents and returns ordered embeddings."""
    chunks = [
        DocumentChunk(
            content="Item 1 Business",
            section_name="item_1",
            chunk_index=0,
            token_count=3,
        ),
        DocumentChunk(
            content="Item 1A Risk Factors",
            section_name="item_1a",
            chunk_index=1,
            token_count=4,
        ),
    ]
    cast(AsyncMock, mock_client.embeddings.create).return_value = make_mock_response(2)

    result = await service.embed_chunks(chunks)

    assert len(result) == 2
    cast(AsyncMock, mock_client.embeddings.create).assert_called_once_with(
        input=["Item 1 Business", "Item 1A Risk Factors"],
        model="text-embedding-3-small",
    )


@pytest.mark.asyncio
async def test_embed_chunks_empty(service: EmbeddingService) -> None:
    """Verify empty chunks sequence returns empty list."""
    result = await service.embed_chunks([])
    assert result == []


@pytest.mark.asyncio
async def test_embed_query_single_text(
    service: EmbeddingService, mock_client: AsyncOpenAI
) -> None:
    """Verify embed_query returns a single 1536-dimensional float vector."""
    cast(AsyncMock, mock_client.embeddings.create).return_value = make_mock_response(1)

    embedding = await service.embed_query("What are cybersecurity risk factors?")

    assert len(embedding) == 1536
    assert isinstance(embedding, list)
    cast(AsyncMock, mock_client.embeddings.create).assert_called_once()


@pytest.mark.asyncio
async def test_embed_retry_on_429_success(
    mock_client: AsyncOpenAI,
) -> None:
    """Verify service retries on HTTP 429 RateLimitError and succeeds."""
    service = EmbeddingService(
        client=mock_client,
        max_retries=3,
        initial_delay=0.001,
    )
    cast(AsyncMock, mock_client.embeddings.create).side_effect = [
        make_rate_limit_error(),
        make_mock_response(1),
    ]

    result = await service.embed_texts(["Retried text"])

    assert len(result) == 1
    assert cast(AsyncMock, mock_client.embeddings.create).call_count == 2


@pytest.mark.asyncio
async def test_embed_retry_exhausted_raises(
    mock_client: AsyncOpenAI,
) -> None:
    """Verify RateLimitExceededError is raised when max retries are exceeded."""
    service = EmbeddingService(
        client=mock_client,
        max_retries=2,
        initial_delay=0.001,
    )
    cast(AsyncMock, mock_client.embeddings.create).side_effect = [
        make_rate_limit_error(),
        make_rate_limit_error(),
        make_rate_limit_error(),
    ]

    with pytest.raises(
        RateLimitExceededError, match="rate limit exceeded after 2 retries"
    ):
        await service.embed_texts(["Failing text"])

    assert cast(AsyncMock, mock_client.embeddings.create).call_count == 3


@pytest.mark.asyncio
async def test_embed_unrecoverable_api_error(
    service: EmbeddingService, mock_client: AsyncOpenAI
) -> None:
    """Verify non-retryable API error raises EmbeddingServiceError immediately."""
    cast(AsyncMock, mock_client.embeddings.create).side_effect = make_auth_error()

    with pytest.raises(
        EmbeddingServiceError, match="OpenAI API error during embedding generation"
    ):
        await service.embed_texts(["Text with auth error"])

    assert cast(AsyncMock, mock_client.embeddings.create).call_count == 1


@pytest.mark.asyncio
async def test_embed_unexpected_error(
    service: EmbeddingService, mock_client: AsyncOpenAI
) -> None:
    """Verify unexpected general exception raises EmbeddingServiceError."""
    cast(AsyncMock, mock_client.embeddings.create).side_effect = RuntimeError(
        "Network connection reset"
    )

    with pytest.raises(
        EmbeddingServiceError, match="Unexpected error during embedding generation"
    ):
        await service.embed_texts(["Text with network error"])


def test_embedding_service_invalid_parameters() -> None:
    """Verify ValueError is raised for invalid constructor parameters."""
    with pytest.raises(ValueError, match="max_batch_size must be positive"):
        EmbeddingService(max_batch_size=0)

    with pytest.raises(ValueError, match="max_retries must be non-negative"):
        EmbeddingService(max_retries=-1)

    with pytest.raises(ValueError, match="initial_delay must be non-negative"):
        EmbeddingService(initial_delay=-0.1)


@pytest.mark.asyncio
async def test_embedding_service_custom_model(
    mock_client: AsyncOpenAI,
) -> None:
    """Verify service respects custom model and dimensions configuration."""
    service = EmbeddingService(
        client=mock_client,
        model="text-embedding-3-large",
        dimensions=3072,
        initial_delay=0.001,
    )
    cast(AsyncMock, mock_client.embeddings.create).return_value = make_mock_response(
        1, dim=3072
    )

    result = await service.embed_texts(["Large embedding test"])

    assert len(result[0]) == 3072
    cast(AsyncMock, mock_client.embeddings.create).assert_called_once_with(
        input=["Large embedding test"],
        model="text-embedding-3-large",
    )


def test_count_tokens(service: EmbeddingService) -> None:
    """Verify count_tokens handles empty strings and valid inputs."""
    assert service.count_tokens("") == 0
    assert service.count_tokens("   ") == 0
    assert service.count_tokens("Valid token count text") > 0
