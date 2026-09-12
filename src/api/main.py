"""FastAPI application initialization and endpoints."""

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request

from src.api.dependencies import (
    get_edgar_client,
    get_filing_downloader,
    get_indexing_pipeline,
    get_rag_pipeline,
    get_vector_store,
)
from src.api.logging import setup_logging
from src.api.schemas import IngestRequest, QueryRequest, QueryResponse
from src.indexing.pipeline import IndexingPipeline
from src.ingestion.edgar_client import EdgarClient
from src.ingestion.filing_downloader import FilingDownloader
from src.ingestion.html_parser import TenKParser
from src.ingestion.models import FilingMetadata, ParsedDocument, ParsedSection
from src.ingestion.section_extractor import SectionExtractor
from src.rag.citations import format_answer_with_citations
from src.rag.pipeline import RAGPipeline

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


async def run_ingestion_pipeline(
    ticker: str,
    cik: str,
    downloader: FilingDownloader,
    pipeline: IndexingPipeline,
) -> None:
    """Background task to run the full ingestion and indexing flow."""
    try:
        logger.info(f"Starting background ingestion for {ticker} (CIK {cik})")
        paths = await downloader.download_recent_10k(cik, limit=1)
        if not paths:
            logger.error(f"No 10-K filings found for CIK {cik}")
            return

        parser = TenKParser()
        extractor = SectionExtractor()

        for path in paths:
            accession_number = path.stem
            
            # 1. Parse HTML
            html_text = parser.parse_file(path)
            
            # 2. Extract Sections
            sections_dict = extractor.extract_sections(html_text)

            # 3. Create Models
            metadata = FilingMetadata(
                cik=cik,
                ticker=ticker,
                period="2023-12-31",  # Placeholder period
                accession_number=accession_number,
                form_type="10-K",
            )

            parsed_sections = [
                ParsedSection(section_name=name, raw_text=text)
                for name, text in sections_dict.items()
            ]

            document = ParsedDocument(
                metadata=metadata,
                sections=parsed_sections,
            )

            # 4. Index Document
            await pipeline.process_document(document, show_progress=False)

        logger.info(f"Ingestion successfully completed for {ticker}")
    except Exception as e:
        logger.exception(f"Error during ingestion pipeline for {ticker}: {e}")


@app.post("/ingest", status_code=202)
async def ingest_document(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    edgar_client: EdgarClient = Depends(get_edgar_client),
    downloader: FilingDownloader = Depends(get_filing_downloader),
    pipeline: IndexingPipeline = Depends(get_indexing_pipeline),
) -> dict[str, str]:
    """Trigger the ingestion pipeline for a ticker."""
    try:
        cik = await edgar_client.get_cik_from_ticker(request.ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
        
    background_tasks.add_task(
        run_ingestion_pipeline,
        ticker=request.ticker.upper(),
        cik=cik,
        downloader=downloader,
        pipeline=pipeline,
    )
    
    return {
        "status": "accepted",
        "message": f"Ingestion started in background for ticker {request.ticker.upper()}",
    }
