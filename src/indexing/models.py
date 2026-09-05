"""Data models for document indexing and semantic chunking."""

from pydantic import BaseModel, field_validator


class DocumentChunk(BaseModel):
    """Represents a text chunk extracted from an SEC filing section."""

    content: str
    section_name: str
    document_id: str | None = None
    chunk_index: int
    token_count: int

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        """Validate content is not empty."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content cannot be empty.")
        return cleaned

    @field_validator("section_name")
    @classmethod
    def validate_section_name(cls, value: str) -> str:
        """Validate and normalize section_name to lowercase."""
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("section_name cannot be empty.")
        return cleaned

    @field_validator("chunk_index")
    @classmethod
    def validate_chunk_index(cls, value: int) -> int:
        """Validate that chunk_index is non-negative."""
        if value < 0:
            raise ValueError("chunk_index must be greater than or equal to 0.")
        return value

    @field_validator("token_count")
    @classmethod
    def validate_token_count(cls, value: int) -> int:
        """Validate that token_count is non-negative."""
        if value < 0:
            raise ValueError("token_count must be greater than or equal to 0.")
        return value
