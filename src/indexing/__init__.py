"""Indexing package for document chunking and embedding pipelines."""

from src.indexing.chunker import SectionAwareChunker
from src.indexing.embeddings import EmbeddingService
from src.indexing.exceptions import (
    EmbeddingServiceError,
    IndexingError,
    RateLimitExceededError,
    TokenLimitExceededError,
)
from src.indexing.models import DocumentChunk

__all__ = [
    "DocumentChunk",
    "EmbeddingService",
    "EmbeddingServiceError",
    "IndexingError",
    "RateLimitExceededError",
    "SectionAwareChunker",
    "TokenLimitExceededError",
]
