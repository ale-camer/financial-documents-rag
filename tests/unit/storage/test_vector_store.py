"""Unit tests for VectorStoreClient using mocked connection pool."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import psycopg
import pytest
from psycopg_pool import AsyncConnectionPool

from src.indexing.models import DocumentChunk
from src.ingestion.models import FilingMetadata
from src.storage.exceptions import (
    ConnectionPoolError,
    VectorStoreError,
)
from src.storage.models import SearchResult
from src.storage.vector_store import VectorStoreClient


class MockAsyncCursor:
    """Mock asynchronous database cursor."""

    def __init__(self) -> None:
        self.execute = AsyncMock()
        self.fetchone = AsyncMock()
        self.fetchall = AsyncMock()

    async def __aenter__(self) -> "MockAsyncCursor":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        pass


class MockAsyncTransaction:
    """Mock asynchronous transaction context manager."""

    async def __aenter__(self) -> "MockAsyncTransaction":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        pass


class MockAsyncConnection:
    """Mock asynchronous database connection."""

    def __init__(self, cursor: MockAsyncCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> MockAsyncCursor:
        return self._cursor

    def transaction(self) -> MockAsyncTransaction:
        return MockAsyncTransaction()


class MockConnectionContext:
    """Mock async context manager returning MockAsyncConnection."""

    def __init__(self, conn: MockAsyncConnection) -> None:
        self._conn = conn

    async def __aenter__(self) -> MockAsyncConnection:
        return self._conn

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        pass


class MockAsyncPool:
    """Mock connection pool providing controlled connection context."""

    def __init__(self, cursor: MockAsyncCursor) -> None:
        self.cursor = cursor
        self.conn = MockAsyncConnection(cursor)
        self.open = AsyncMock()
        self.close = AsyncMock()

    def connection(self) -> MockConnectionContext:
        return MockConnectionContext(self.conn)


@pytest.fixture
def mock_cursor() -> MockAsyncCursor:
    """Fixture providing a configured MockAsyncCursor."""
    return MockAsyncCursor()


@pytest.fixture
def mock_pool(mock_cursor: MockAsyncCursor) -> MockAsyncPool:
    """Fixture providing a configured MockAsyncPool."""
    return MockAsyncPool(mock_cursor)


@pytest.fixture
def sample_metadata() -> FilingMetadata:
    """Fixture providing valid FilingMetadata."""
    return FilingMetadata(
        cik="0000320193",
        ticker="AAPL",
        period="2023-09-30",
        form_type="10-K",
        accession_number="0000320193-23-000106",
    )


@pytest.fixture
def sample_chunks() -> list[DocumentChunk]:
    """Fixture providing two valid DocumentChunks."""
    return [
        DocumentChunk(
            content="Item 1 Business description text.",
            section_name="item_1",
            chunk_index=0,
            token_count=6,
        ),
        DocumentChunk(
            content="Item 1A Risk factors text.",
            section_name="item_1a",
            chunk_index=1,
            token_count=6,
        ),
    ]


def test_client_init_invalid_args() -> None:
    """Verify ValueError is raised for invalid min_size or max_size."""
    with pytest.raises(ValueError, match="min_size must be at least 1"):
        VectorStoreClient(min_size=0)

    with pytest.raises(ValueError, match="max_size must be greater"):
        VectorStoreClient(min_size=5, max_size=2)


@pytest.mark.asyncio
async def test_client_open_and_close(mock_pool: MockAsyncPool) -> None:
    """Verify client opens and closes internal pool."""
    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    await client.open()
    mock_pool.open.assert_awaited_once()

    await client.close()
    mock_pool.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_client_async_context_manager(mock_pool: MockAsyncPool) -> None:
    """Verify async context manager opens and closes pool automatically."""
    pool_mock = cast(AsyncConnectionPool, mock_pool)
    async with VectorStoreClient(pool=pool_mock) as client:
        assert client is not None
        mock_pool.open.assert_awaited_once()

    mock_pool.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_client_open_error_handling() -> None:
    """Verify ConnectionPoolError is raised when opening pool fails."""
    pool = MagicMock(spec=AsyncConnectionPool)
    pool.open = AsyncMock(side_effect=RuntimeError("Connection refused"))
    client = VectorStoreClient(pool=pool)

    with pytest.raises(ConnectionPoolError, match="Failed to open"):
        await client.open()


@pytest.mark.asyncio
async def test_client_close_error_handling() -> None:
    """Verify ConnectionPoolError is raised when closing pool fails."""
    pool = MagicMock(spec=AsyncConnectionPool)
    pool.close = AsyncMock(side_effect=RuntimeError("Teardown error"))
    client = VectorStoreClient(pool=pool)

    with pytest.raises(ConnectionPoolError, match="Failed to close"):
        await client.close()


def test_get_pool_unopened_raises() -> None:
    """Verify ConnectionPoolError is raised when client is not open."""
    client = VectorStoreClient()
    with pytest.raises(ConnectionPoolError, match="Connection pool is not open"):
        client._get_pool()


@pytest.mark.asyncio
async def test_upsert_document_success(
    mock_pool: MockAsyncPool,
    mock_cursor: MockAsyncCursor,
    sample_metadata: FilingMetadata,
) -> None:
    """Verify upsert_document executes query and returns generated UUID."""
    expected_id = uuid4()
    mock_cursor.fetchone.return_value = (str(expected_id),)

    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    doc_id = await client.upsert_document(sample_metadata)

    assert doc_id == expected_id
    mock_cursor.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_document_db_error(
    mock_pool: MockAsyncPool,
    mock_cursor: MockAsyncCursor,
    sample_metadata: FilingMetadata,
) -> None:
    """Verify psycopg.Error in upsert_document is wrapped in VectorStoreError."""
    mock_cursor.execute.side_effect = psycopg.DatabaseError("Syntax error")

    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    with pytest.raises(VectorStoreError, match="Database error upserting document"):
        await client.upsert_document(sample_metadata)


@pytest.mark.asyncio
async def test_upsert_chunks_empty(mock_pool: MockAsyncPool) -> None:
    """Verify upsert_chunks returns empty list when given no chunks."""
    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    result = await client.upsert_chunks(uuid4(), [])
    assert result == []


@pytest.mark.asyncio
async def test_upsert_chunks_success(
    mock_pool: MockAsyncPool,
    mock_cursor: MockAsyncCursor,
    sample_chunks: list[DocumentChunk],
) -> None:
    """Verify upsert_chunks executes batch insertion and returns UUID list."""
    id1, id2 = uuid4(), uuid4()
    mock_cursor.fetchone.side_effect = [(str(id1),), (str(id2),)]

    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    doc_id = uuid4()
    chunk_ids = await client.upsert_chunks(doc_id, sample_chunks)

    assert chunk_ids == [id1, id2]
    assert mock_cursor.execute.await_count == 2


@pytest.mark.asyncio
async def test_upsert_embeddings_length_mismatch(mock_pool: MockAsyncPool) -> None:
    """Verify ValueError is raised when chunk_ids and embeddings lengths differ."""
    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    with pytest.raises(ValueError, match="must have identical lengths"):
        await client.upsert_embeddings([uuid4()], [])


@pytest.mark.asyncio
async def test_upsert_embeddings_empty(mock_pool: MockAsyncPool) -> None:
    """Verify upsert_embeddings returns immediately when given empty lists."""
    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    await client.upsert_embeddings([], [])


@pytest.mark.asyncio
async def test_upsert_embeddings_success(
    mock_pool: MockAsyncPool,
    mock_cursor: MockAsyncCursor,
) -> None:
    """Verify upsert_embeddings executes SQL for each chunk vector."""
    c_ids = [uuid4(), uuid4()]
    embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    await client.upsert_embeddings(c_ids, embeddings)
    assert mock_cursor.execute.await_count == 2


@pytest.mark.asyncio
async def test_similarity_search_invalid_top_k(mock_pool: MockAsyncPool) -> None:
    """Verify ValueError is raised when top_k <= 0."""
    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        await client.similarity_search([0.1, 0.2], top_k=0)


@pytest.mark.asyncio
async def test_similarity_search_no_filter(
    mock_pool: MockAsyncPool,
    mock_cursor: MockAsyncCursor,
) -> None:
    """Verify similarity_search returns mapped SearchResult instances."""
    c_id, d_id = uuid4(), uuid4()
    mock_cursor.fetchall.return_value = [
        (
            str(c_id),
            str(d_id),
            "Chunk content",
            "item_1",
            0,
            0.92,
            "0000320193",
            "AAPL",
            "2023-09-30",
            "10-K",
            "0000320193-23-000106",
        )
    ]

    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    results = await client.similarity_search([0.1, 0.2], top_k=3)

    assert len(results) == 1
    res = results[0]
    assert isinstance(res, SearchResult)
    assert res.chunk_id == c_id
    assert res.document_id == d_id
    assert res.similarity == 0.92
    assert res.document_metadata["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_similarity_search_with_filters(
    mock_pool: MockAsyncPool,
    mock_cursor: MockAsyncCursor,
) -> None:
    """Verify similarity_search appends WHERE clauses for metadata filters."""
    mock_cursor.fetchall.return_value = []

    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    filters = {"ticker": "MSFT", "section_name": "item_7", "period": "2023-12-31"}
    results = await client.similarity_search([0.1, 0.2], top_k=5, filters=filters)

    assert results == []
    query, params = mock_cursor.execute.call_args[0]
    assert "d.ticker = %s" in query
    assert "c.section_name = %s" in query
    assert "d.period = %s" in query
    assert "MSFT" in params
    assert "item_7" in params


@pytest.mark.asyncio
async def test_similarity_search_empty_results(
    mock_pool: MockAsyncPool,
    mock_cursor: MockAsyncCursor,
) -> None:
    """Verify similarity_search returns empty list when no rows returned."""
    mock_cursor.fetchall.return_value = []

    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    results = await client.similarity_search([0.5, 0.5])
    assert results == []


@pytest.mark.asyncio
async def test_delete_document_success(
    mock_pool: MockAsyncPool,
    mock_cursor: MockAsyncCursor,
) -> None:
    """Verify delete_document returns True when document row was deleted."""
    target_id = uuid4()
    mock_cursor.fetchone.return_value = (str(target_id),)

    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    deleted = await client.delete_document(target_id)
    assert deleted is True


@pytest.mark.asyncio
async def test_delete_document_not_found(
    mock_pool: MockAsyncPool,
    mock_cursor: MockAsyncCursor,
) -> None:
    """Verify delete_document returns False when no document row matched."""
    mock_cursor.fetchone.return_value = None

    pool_mock = cast(AsyncConnectionPool, mock_pool)
    client = VectorStoreClient(pool=pool_mock)

    deleted = await client.delete_document(uuid4())
    assert deleted is False
