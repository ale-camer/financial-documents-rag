"""Pydantic schemas for the FastAPI service."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    """Request schema for RAG queries."""

    query: str = Field(..., description="The user's question")
    filters: dict[str, Any] | None = Field(
        default=None, description="Metadata filters (e.g., ticker)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "Riesgos en cadena de suministro?",
                    "filters": {"ticker": "AAPL"},
                }
            ]
        }
    )


class QueryResponse(BaseModel):
    """Response schema for RAG queries."""

    answer: str = Field(..., description="The generated answer")
    source_documents: list[dict[str, Any]] = Field(
        default_factory=list, description="The chunks used to generate the answer"
    )
    citations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Structured citations extracted from the answer",
    )


class IngestRequest(BaseModel):
    """Request schema for document ingestion."""

    ticker: str = Field(..., description="Company ticker")
    form_type: str = Field(default="10-K", description="Form type")

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"ticker": "AAPL", "form_type": "10-K"}]}
    )


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""

    status: str = Field(..., description="Service status", examples=["ok"])


class IngestResponse(BaseModel):
    """Response schema for document ingestion endpoint."""

    status: str = Field(..., description="Ingestion status", examples=["accepted"])
    message: str = Field(
        ...,
        description="Detailed status message",
        examples=["Ingestion started in background for ticker AAPL"],
    )
