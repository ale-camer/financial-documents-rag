"""Pydantic schemas for the FastAPI service."""

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request schema for RAG queries."""

    query: str = Field(..., description="The user's question")
    filters: dict[str, Any] | None = Field(
        default=None, description="Metadata filters (e.g., ticker)"
    )


class QueryResponse(BaseModel):
    """Response schema for RAG queries."""

    answer: str = Field(..., description="The generated answer")
    source_documents: list[dict[str, Any]] = Field(
        default_factory=list, description="The chunks used to generate the answer"
    )


class IngestRequest(BaseModel):
    """Request schema for document ingestion."""

    ticker: str = Field(..., description="Company ticker")
    form_type: str = Field(default="10-K", description="Form type")
