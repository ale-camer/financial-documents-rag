"""Custom domain exceptions for document indexing and embeddings."""


class IndexingError(Exception):
    """Base exception for indexing and embedding operations."""


class TokenLimitExceededError(IndexingError):
    """Raised when an input text exceeds the model token limit (8191 tokens)."""


class EmbeddingServiceError(IndexingError):
    """Raised on unrecoverable API errors during embedding generation."""


class RateLimitExceededError(EmbeddingServiceError):
    """Raised when OpenAI rate limit retries are exhausted."""
