"""Data models for storage and retrieval operations."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SearchResult(BaseModel):
    """Retrieved chunk result with similarity score and metadata."""

    model_config = ConfigDict(frozen=True)

    chunk_id: UUID
    document_id: UUID
    content: str
    section_name: str
    chunk_index: int
    similarity: float
    document_metadata: dict[str, Any]
