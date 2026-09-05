"""Vector store client providing CRUD and similarity search on pgvector."""

import os
from collections.abc import Sequence
from typing import Any
from uuid import UUID

import psycopg
from psycopg_pool import AsyncConnectionPool

from src.indexing.models import DocumentChunk
from src.ingestion.models import FilingMetadata
from src.storage.exceptions import (
    ConnectionPoolError,
    VectorStoreError,
)
from src.storage.models import SearchResult

DEFAULT_MIN_POOL_SIZE = 1
DEFAULT_MAX_POOL_SIZE = 10
DEFAULT_MODEL_NAME = "text-embedding-3-small"


def _format_vector(vector: Sequence[float]) -> str:
    """Format a sequence of floats as a PostgreSQL pgvector literal string."""
    return f"[{','.join(str(v) for v in vector)}]"


def _build_default_connection_string() -> str:
    """Construct PostgreSQL connection string from environment variables."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "financial_rag")
    user = os.getenv("POSTGRES_USER", "rag_user")
    password = os.getenv("POSTGRES_PASSWORD", "changeme")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


class VectorStoreClient:
    """Asynchronous client for pgvector document, chunk, and embedding storage."""

    def __init__(
        self,
        connection_string: str | None = None,
        min_size: int = DEFAULT_MIN_POOL_SIZE,
        max_size: int = DEFAULT_MAX_POOL_SIZE,
        pool: AsyncConnectionPool | None = None,
    ) -> None:
        """Initialize VectorStoreClient with connection parameters or pool."""
        if min_size < 1:
            raise ValueError("min_size must be at least 1.")
        if max_size < min_size:
            raise ValueError("max_size must be greater than or equal to min_size.")

        self._connection_string = (
            connection_string or _build_default_connection_string()
        )
        self._min_size = min_size
        self._max_size = max_size
        self._pool = pool
        self._owns_pool = pool is None

    async def open(self) -> None:
        """Initialize and open the asynchronous connection pool."""
        if self._pool is None:
            self._pool = AsyncConnectionPool(
                conninfo=self._connection_string,
                min_size=self._min_size,
                max_size=self._max_size,
                open=False,
            )
        try:
            await self._pool.open()
        except Exception as err:
            raise ConnectionPoolError(f"Failed to open connection pool: {err}") from err

    async def close(self) -> None:
        """Close the connection pool and release resources."""
        if self._pool is not None:
            try:
                await self._pool.close()
            except Exception as err:
                raise ConnectionPoolError(
                    f"Failed to close connection pool: {err}"
                ) from err
            finally:
                if self._owns_pool:
                    self._pool = None

    async def __aenter__(self) -> "VectorStoreClient":
        """Enter async context manager, opening connection pool."""
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager, closing connection pool."""
        await self.close()

    def _get_pool(self) -> AsyncConnectionPool:
        """Return the active connection pool or raise ConnectionPoolError."""
        if self._pool is None:
            raise ConnectionPoolError("Connection pool is not open. Call open() first.")
        return self._pool

    async def upsert_document(self, metadata: FilingMetadata) -> UUID:
        """Insert or update a filing document and return its UUID."""
        pool = self._get_pool()
        query = """
        INSERT INTO documents (cik, ticker, period, form_type, accession_number)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (accession_number) DO UPDATE SET
            cik = EXCLUDED.cik,
            ticker = EXCLUDED.ticker,
            period = EXCLUDED.period,
            form_type = EXCLUDED.form_type
        RETURNING id;
        """
        try:
            async with pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(
                    query,
                    (
                        metadata.cik,
                        metadata.ticker,
                        metadata.period,
                        metadata.form_type,
                        metadata.accession_number,
                    ),
                )
                row = await cur.fetchone()
                if row is None:
                    raise VectorStoreError("Failed to retrieve upserted document ID.")
                return UUID(str(row[0]))
        except psycopg.Error as err:
            raise VectorStoreError(f"Database error upserting document: {err}") from err

    async def upsert_chunks(
        self, document_id: UUID, chunks: Sequence[DocumentChunk]
    ) -> list[UUID]:
        """Insert or update chunks for a document, returning chunk UUIDs."""
        if not chunks:
            return []

        pool = self._get_pool()
        query = """
        INSERT INTO chunks (
            document_id, section_name, content, token_count, chunk_index
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (document_id, chunk_index) DO UPDATE SET
            section_name = EXCLUDED.section_name,
            content = EXCLUDED.content,
            token_count = EXCLUDED.token_count
        RETURNING id;
        """
        chunk_ids: list[UUID] = []
        try:
            async with (
                pool.connection() as conn,
                conn.transaction(),
                conn.cursor() as cur,
            ):
                for chunk in chunks:
                    await cur.execute(
                        query,
                        (
                            document_id,
                            chunk.section_name,
                            chunk.content,
                            chunk.token_count,
                            chunk.chunk_index,
                        ),
                    )
                    row = await cur.fetchone()
                    if row is None:
                        raise VectorStoreError("Failed to retrieve upserted chunk ID.")
                    chunk_ids.append(UUID(str(row[0])))
            return chunk_ids
        except psycopg.Error as err:
            raise VectorStoreError(f"Database error upserting chunks: {err}") from err

    async def upsert_embeddings(
        self,
        chunk_ids: Sequence[UUID],
        embeddings: Sequence[list[float]],
        model_name: str = DEFAULT_MODEL_NAME,
    ) -> None:
        """Insert or update dense vector embeddings for corresponding chunk IDs."""
        if len(chunk_ids) != len(embeddings):
            raise ValueError(
                f"chunk_ids ({len(chunk_ids)}) and embeddings "
                f"({len(embeddings)}) must have identical lengths."
            )
        if not chunk_ids:
            return

        pool = self._get_pool()
        query = """
        INSERT INTO embeddings (chunk_id, embedding, model_name)
        VALUES (%s, %s::vector, %s)
        ON CONFLICT (chunk_id) DO UPDATE SET
            embedding = EXCLUDED.embedding,
            model_name = EXCLUDED.model_name;
        """
        try:
            async with (
                pool.connection() as conn,
                conn.transaction(),
                conn.cursor() as cur,
            ):
                for chunk_id, embedding in zip(chunk_ids, embeddings, strict=True):
                    vec_str = _format_vector(embedding)
                    await cur.execute(query, (chunk_id, vec_str, model_name))
        except psycopg.Error as err:
            raise VectorStoreError(
                f"Database error upserting embeddings: {err}"
            ) from err

    async def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Perform HNSW cosine distance vector search with optional filters."""
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        pool = self._get_pool()
        vec_str = _format_vector(query_vector)

        where_clauses: list[str] = []
        filter_params: list[Any] = []

        if filters:
            allowed_column_map = {
                "ticker": "d.ticker",
                "cik": "d.cik",
                "section_name": "c.section_name",
                "form_type": "d.form_type",
                "period": "d.period",
            }
            for key, val in filters.items():
                if key in allowed_column_map and val is not None:
                    col = allowed_column_map[key]
                    where_clauses.append(f"{col} = %s")
                    filter_params.append(val)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        query = f"""
        SELECT
            c.id AS chunk_id,
            c.document_id,
            c.content,
            c.section_name,
            c.chunk_index,
            1 - (e.embedding <=> %s::vector) AS similarity,
            d.cik,
            d.ticker,
            d.period,
            d.form_type,
            d.accession_number
        FROM embeddings e
        JOIN chunks c ON e.chunk_id = c.id
        JOIN documents d ON c.document_id = d.id
        {where_sql}
        ORDER BY e.embedding <=> %s::vector ASC
        LIMIT %s;
        """
        params: list[Any] = [vec_str, *filter_params, vec_str, top_k]

        try:
            async with pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(query, tuple(params))
                rows = await cur.fetchall()

            results: list[SearchResult] = []
            for row in rows:
                results.append(
                    SearchResult(
                        chunk_id=UUID(str(row[0])),
                        document_id=UUID(str(row[1])),
                        content=str(row[2]),
                        section_name=str(row[3]),
                        chunk_index=int(row[4]),
                        similarity=float(row[5]),
                        document_metadata={
                            "cik": str(row[6]),
                            "ticker": row[7],
                            "period": str(row[8]),
                            "form_type": str(row[9]),
                            "accession_number": str(row[10]),
                        },
                    )
                )
            return results
        except psycopg.Error as err:
            raise VectorStoreError(
                f"Database error during vector search: {err}"
            ) from err

    async def delete_document(self, document_id: UUID) -> bool:
        """Delete document by UUID, cascading to chunks and embeddings."""
        pool = self._get_pool()
        query = "DELETE FROM documents WHERE id = %s RETURNING id;"
        try:
            async with pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(query, (document_id,))
                row = await cur.fetchone()
                return row is not None
        except psycopg.Error as err:
            raise VectorStoreError(f"Database error deleting document: {err}") from err
