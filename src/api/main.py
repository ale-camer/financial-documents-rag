"""FastAPI application initialization and endpoints."""

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request

from src.api.dependencies import get_rag_pipeline, get_vector_store
from src.api.schemas import IngestRequest, QueryRequest, QueryResponse
from src.rag.citations import format_answer_with_citations
from src.rag.pipeline import RAGPipeline
from src.api.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events like opening/closing database connections."""
    setup_logging()
    vector_store = get_vector_store()
    try:
        await vector_store.open()
        yield
    finally:
        await vector_store.close()


app = FastAPI(
    title="Financial Documents RAG",
    description="RAG API for querying SEC 10-K filings.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log HTTP request latency and status."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - Status: {response.status_code} - Latency: {process_time:.4f}s"
    )
    return response


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return a basic health check response."""
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> QueryResponse:
    """Process a natural language query using the RAG pipeline."""
    try:
        result = await pipeline.ask(query=request.query, filters=request.filters)

        formatted_result = format_answer_with_citations(
            result["answer"], result["source_documents"]
        )

        sources = [
            chunk.model_dump(mode="json") for chunk in result["source_documents"]
        ]
        return QueryResponse(
            answer=formatted_result["answer"],
            source_documents=sources,
            citations=formatted_result["citations"],
        )
    except Exception as e:
        logger.exception("Error processing query")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/ingest")
async def ingest_document(request: IngestRequest) -> dict[str, str]:
    """Trigger the ingestion pipeline for a ticker (stub for now)."""
    # TODO: Implement the actual ingestion pipeline integration
    return {"status": "accepted", "message": f"Ingestion started for {request.ticker}"}
