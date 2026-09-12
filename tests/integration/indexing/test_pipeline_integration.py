"""Integration tests for IndexingPipeline against live PostgreSQL and pgvector."""

from collections.abc import Sequence
from uuid import uuid4

import pytest

from src.indexing.chunker import SectionAwareChunker
from src.indexing.embeddings import EmbeddingService
from src.indexing.models import DocumentChunk
from src.indexing.pipeline import IndexingPipeline
from src.ingestion.models import FilingMetadata, ParsedDocument, ParsedSection
from src.storage.vector_store import VectorStoreClient


class MockEmbeddingService(EmbeddingService):
    """Mock EmbeddingService returning dummy values."""

    def __init__(self, value: float) -> None:
        super().__init__(api_key="dummy")
        self.value = value

    async def embed_chunks(self, chunks: Sequence[DocumentChunk]) -> list[list[float]]:
        return [[self.value] * 1536 for _ in chunks]


def _is_db_reachable() -> bool:
    """Check if PostgreSQL database is reachable."""
    try:
        import psycopg

        from src.storage.vector_store import _build_default_connection_string

        conninfo = _build_default_connection_string()
        with (
            psycopg.connect(conninfo, connect_timeout=2) as conn,
            conn.cursor() as cur,
        ):
            cur.execute("SELECT 1;")
            return True
    except Exception:
        return False


db_required = pytest.mark.skipif(
    not _is_db_reachable(),
    reason="PostgreSQL / pgvector database is not accessible.",
)


@pytest.fixture
def dummy_document() -> ParsedDocument:
    """Create a sample 10-K document."""
    unique_acc = f"0000320193-23-{uuid4().hex[:6]}"
    metadata = FilingMetadata(
        cik="0000320193",
        ticker="AAPL",
        period="2023-09-30",
        form_type="10-K",
        accession_number=unique_acc,
    )
    sections = [
        ParsedSection(
            section_name="item_1",
            raw_text=(
                "Apple Inc. designs, manufactures and markets smartphones, "
                "personal computers, tablets, wearables and accessories, "
                "and sells a variety of related services."
            ),
        ),
        ParsedSection(
            section_name="item_1a",
            raw_text=(
                "Global markets for the Company’s products and services "
                "are highly competitive and subject to rapid technological change."
            ),
        ),
    ]
    return ParsedDocument(metadata=metadata, sections=sections)


@pytest.mark.asyncio
@db_required
async def test_indexing_pipeline_end_to_end(dummy_document: ParsedDocument) -> None:
    """Run process_document and verify database state."""
    chunker = SectionAwareChunker(chunk_size=128, chunk_overlap=16)
    embedding_service = MockEmbeddingService(value=0.01)

    async with VectorStoreClient() as vector_store:
        pipeline = IndexingPipeline(
            chunker=chunker,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

        await pipeline.process_document(
            document=dummy_document,
            batch_size=2,
            concurrency=2,
            show_progress=False,
        )

        # Verify document was created
        results = await vector_store.similarity_search(
            query_vector=[0.01] * 1536,
            top_k=10,
            filters={"ticker": "AAPL"},
        )
        assert len(results) > 0
        assert all(r.document_metadata["ticker"] == "AAPL" for r in results)

        # Clean up
        doc_id = results[0].document_id
        await vector_store.delete_document(doc_id)


@pytest.mark.asyncio
@db_required
async def test_indexing_pipeline_idempotency(dummy_document: ParsedDocument) -> None:
    """Re-index the same document and ensure chunks/embeddings are updated."""
    chunker = SectionAwareChunker(chunk_size=128, chunk_overlap=16)
    embedding_service = MockEmbeddingService(value=0.02)

    async with VectorStoreClient() as vector_store:
        pipeline = IndexingPipeline(
            chunker=chunker,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

        # First run
        await pipeline.process_document(
            document=dummy_document,
            batch_size=2,
            concurrency=2,
            show_progress=False,
        )

        # Verify first run
        results1 = await vector_store.similarity_search(
            query_vector=[0.02] * 1536,
            top_k=10,
            filters={"accession_number": dummy_document.metadata.accession_number},
        )
        assert len(results1) > 0
        doc_id = results1[0].document_id

        # Modify document
        dummy_document.sections[0].raw_text = "Updated Apple Inc. description."

        # Second run
        embedding_service = MockEmbeddingService(value=0.03)
        pipeline.embedding_service = embedding_service
        await pipeline.process_document(
            document=dummy_document,
            batch_size=2,
            concurrency=2,
            show_progress=False,
        )

        # Verify second run
        results2 = await vector_store.similarity_search(
            query_vector=[0.03] * 1536,
            top_k=10,
            filters={"accession_number": dummy_document.metadata.accession_number},
        )

        # Ensure document ID remains the same
        assert len(results2) == len(results1)
        assert all(r.document_id == doc_id for r in results2)

        # The content should be updated
        updated_chunk = next(r for r in results2 if r.section_name == "item_1")
        assert updated_chunk.content == "Updated Apple Inc. description."

        # Clean up
        await vector_store.delete_document(doc_id)
