"""Custom domain exceptions for storage and vector store operations."""


class StorageError(Exception):
    """Base exception for storage operations."""


class VectorStoreError(StorageError):
    """Raised when a vector store query, transaction, or execution fails."""


class DocumentNotFoundError(VectorStoreError):
    """Raised when an operation targets a document that does not exist."""


class ConnectionPoolError(VectorStoreError):
    """Raised when connection pool initialization, acquisition, or cleanup fails."""
