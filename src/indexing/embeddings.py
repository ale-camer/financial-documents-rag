"""OpenAI embeddings service for document chunks."""

import asyncio
from collections.abc import Sequence

import openai
import tiktoken
from openai import AsyncOpenAI
from openai import RateLimitError as OpenAIRateLimitError

from src.indexing.exceptions import (
    EmbeddingServiceError,
    RateLimitExceededError,
    TokenLimitExceededError,
)
from src.indexing.models import DocumentChunk

DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_DIMENSIONS = 1536
MAX_TOKENS_PER_INPUT = 8191
MAX_BATCH_SIZE = 2048
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_DELAY = 0.5


class EmbeddingService:
    """Service to generate dense vector embeddings using OpenAI API."""

    def __init__(
        self,
        client: AsyncOpenAI | None = None,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        dimensions: int = DEFAULT_DIMENSIONS,
        max_batch_size: int = MAX_BATCH_SIZE,
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_delay: float = DEFAULT_INITIAL_DELAY,
        encoding_name: str = "cl100k_base",
    ) -> None:
        """Initialize EmbeddingService with client and configuration."""
        if max_batch_size <= 0:
            raise ValueError("max_batch_size must be positive.")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative.")
        if initial_delay < 0:
            raise ValueError("initial_delay must be non-negative.")

        self.client = client or AsyncOpenAI(api_key=api_key)
        self.model = model
        self.dimensions = dimensions
        self.max_batch_size = max_batch_size
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.tokenizer = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using the configured tiktoken encoding."""
        if not text or not text.strip():
            return 0
        return len(self.tokenizer.encode(text))

    def validate_input_tokens(self, text: str) -> None:
        """Validate that text does not exceed the model token limit."""
        token_count = self.count_tokens(text)
        if token_count > MAX_TOKENS_PER_INPUT:
            raise TokenLimitExceededError(
                f"Input text exceeds maximum limit of {MAX_TOKENS_PER_INPUT} "
                f"tokens (got {token_count})."
            )

    async def _call_embeddings_api(self, batch: list[str]) -> list[list[float]]:
        """Call OpenAI embeddings API with exponential backoff on 429."""
        retries = 0
        delay = self.initial_delay

        while True:
            try:
                response = await self.client.embeddings.create(
                    input=batch,
                    model=self.model,
                )
                sorted_data = sorted(response.data, key=lambda item: item.index)
                return [item.embedding for item in sorted_data]
            except OpenAIRateLimitError as exc:
                retries += 1
                if retries > self.max_retries:
                    raise RateLimitExceededError(
                        f"OpenAI rate limit exceeded after {self.max_retries} retries."
                    ) from exc
                await asyncio.sleep(delay)
                delay *= 2.0
            except openai.APIError as exc:
                raise EmbeddingServiceError(
                    f"OpenAI API error during embedding generation: {exc}"
                ) from exc
            except Exception as exc:
                raise EmbeddingServiceError(
                    f"Unexpected error during embedding generation: {exc}"
                ) from exc

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embeddings for a list of texts with batching."""
        if not texts:
            return []

        for text in texts:
            self.validate_input_tokens(text)

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.max_batch_size):
            batch = texts[i : i + self.max_batch_size]
            batch_embeddings = await self._call_embeddings_api(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def embed_chunks(self, chunks: Sequence[DocumentChunk]) -> list[list[float]]:
        """Generate embeddings for a sequence of DocumentChunk instances."""
        if not chunks:
            return []
        texts = [chunk.content for chunk in chunks]
        return await self.embed_texts(texts)

    async def embed_query(self, query: str) -> list[float]:
        """Generate a single embedding vector for a retrieval query."""
        self.validate_input_tokens(query)
        embeddings = await self.embed_texts([query])
        return embeddings[0]
