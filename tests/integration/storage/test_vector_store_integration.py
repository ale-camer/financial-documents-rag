"""Integration tests for VectorStoreClient against live PostgreSQL and pgvector."""

from uuid import uuid4

import psycopg
import pytest

from src.indexing.models import DocumentChunk
from src.ingestion.models import FilingMetadata
from src.storage.vector_store import (
    VectorStoreClient,
    _build_default_connection_string,
)


def _is_db_reachable() -> bool:
    """Check if PostgreSQL database is reachable."""
    try:
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


@pytest.mark.asyncio
@db_required
async def test_full_crud_lifecycle_live_pgvector() -> None:
    """Verify document upsert, chunk storage, embedding, search, and delete."""
    async with VectorStoreClient() as client:
        unique_acc = f"0000320193-23-{uuid4().hex[:6]}"
        meta = FilingMetadata(
            cik="0000320193",
            ticker="AAPL",
            period="2023-09-30",
            form_type="10-K",
            accession_number=unique_acc,
        )

        doc_id = await client.upsert_document(meta)
        assert doc_id is not None

        chunks = [
            DocumentChunk(
                content="Live test business section overview.",
                section_name="item_1",
                chunk_index=0,
                token_count=5,
            )
        ]
        chunk_ids = await client.upsert_chunks(doc_id, chunks)
        assert len(chunk_ids) == 1

        emb = [0.01] * 1536
        await client.upsert_embeddings(chunk_ids, [emb])

        results = await client.similarity_search(
            query_vector=emb,
            top_k=1,
            filters={"ticker": "AAPL"},
        )
        assert len(results) >= 1
        assert results[0].chunk_id == chunk_ids[0]

        deleted = await client.delete_document(doc_id)
        assert deleted is True


@pytest.mark.asyncio
@db_required
async def test_cascade_delete_live_pgvector() -> None:
    """Verify cascade delete removes chunks and embeddings on document delete."""
    async with VectorStoreClient() as client:
        unique_acc = f"0000789019-23-{uuid4().hex[:6]}"
        meta = FilingMetadata(
            cik="0000789019",
            ticker="MSFT",
            period="2023-06-30",
            form_type="10-K",
            accession_number=unique_acc,
        )

        doc_id = await client.upsert_document(meta)
        chunks = [
            DocumentChunk(
                content="MSFT risk factor chunk content.",
                section_name="item_1a",
                chunk_index=0,
                token_count=5,
            )
        ]
        chunk_ids = await client.upsert_chunks(doc_id, chunks)
        await client.upsert_embeddings(chunk_ids, [[0.05] * 1536])

        deleted = await client.delete_document(doc_id)
        assert deleted is True

        results = await client.similarity_search(
            query_vector=[0.05] * 1536,
            top_k=5,
            filters={"accession_number": unique_acc},
        )
        assert all(r.document_id != doc_id for r in results)


@pytest.mark.asyncio
@db_required
async def test_similarity_search_top_k_ordering() -> None:
    """Verify similarity search returns nearest vector first."""
    async with VectorStoreClient() as client:
        unique_acc = f"0001018724-23-{uuid4().hex[:6]}"
        meta = FilingMetadata(
            cik="0001018724",
            ticker="AMZN",
            period="2023-12-31",
            form_type="10-K",
            accession_number=unique_acc,
        )

        doc_id = await client.upsert_document(meta)
        chunks = [
            DocumentChunk(
                content="Exact match content.",
                section_name="item_7",
                chunk_index=0,
                token_count=3,
            ),
            DocumentChunk(
                content="Distant content.",
                section_name="item_7",
                chunk_index=1,
                token_count=2,
            ),
        ]
        chunk_ids = await client.upsert_chunks(doc_id, chunks)

        target_emb = [0.1] * 1536
        distant_emb = [-0.1] * 1536
        await client.upsert_embeddings(chunk_ids, [target_emb, distant_emb])

        results = await client.similarity_search(
            query_vector=target_emb,
            top_k=2,
            filters={"ticker": "AMZN"},
        )
        assert len(results) >= 2
        assert results[0].chunk_id == chunk_ids[0]
        assert results[0].similarity > results[1].similarity

        await client.delete_document(doc_id)
