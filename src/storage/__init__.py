"""Storage package for PostgreSQL, pgvector schema, and vector store client."""

from src.storage.exceptions import (
    ConnectionPoolError,
    DocumentNotFoundError,
    StorageError,
    VectorStoreError,
)
from src.storage.migration_runner import (
    apply_migrations,
    ensure_migrations_table,
    get_applied_migrations,
    get_migrations_dir,
    rollback_migration,
)
from src.storage.models import SearchResult
from src.storage.vector_store import VectorStoreClient

__all__ = [
    "ConnectionPoolError",
    "DocumentNotFoundError",
    "SearchResult",
    "StorageError",
    "VectorStoreClient",
    "VectorStoreError",
    "apply_migrations",
    "ensure_migrations_table",
    "get_applied_migrations",
    "get_migrations_dir",
    "rollback_migration",
]
