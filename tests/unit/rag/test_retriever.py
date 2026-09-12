"""Unit tests for SemanticRetriever."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.indexing.embeddings import EmbeddingService
from src.rag.models import RetrievedChunk
from src.rag.retriever import HybridRetriever, KeywordRetriever, SemanticRetriever
from src.storage.models import SearchResult
from src.storage.vector_store import VectorStoreClient


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Mock EmbeddingService with embed_query method."""
    service = MagicMock(spec=EmbeddingService)
    service.embed_query = AsyncMock(return_value=[0.1] * 1536)
    return service


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Mock VectorStoreClient with similarity_search method."""
    store = MagicMock(spec=VectorStoreClient)

    # Create some dummy search results
    dummy_results = [
        SearchResult(
            chunk_id=uuid4(),
            document_id=uuid4(),
            content="Dummy content 1",
            section_name="item_1",
            chunk_index=0,
            similarity=0.9,
            document_metadata={"ticker": "AAPL"},
        ),
        SearchResult(
            chunk_id=uuid4(),
            document_id=uuid4(),
            content="Dummy content 2",
            section_name="item_1a",
            chunk_index=1,
            similarity=0.8,
            document_metadata={"ticker": "AAPL"},
        ),
    ]
    store.similarity_search = AsyncMock(return_value=dummy_results)
    return store


@pytest.mark.asyncio
async def test_retrieve_success(
    mock_embedding_service: MagicMock,
    mock_vector_store: MagicMock,
) -> None:
    """Test successful retrieval flow."""
    retriever = SemanticRetriever(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
    )

    results = await retriever.retrieve("test query", top_k=2)

    # Verify embeddings were generated
    mock_embedding_service.embed_query.assert_called_once_with("test query")

    # Verify vector store was queried
    mock_vector_store.similarity_search.assert_called_once_with(
        query_vector=[0.1] * 1536,
        top_k=2,
        filters=None,
    )

    # Verify results mapping
    assert len(results) == 2
    assert results[0].content == "Dummy content 1"
    assert type(results[0]).__name__ == "RetrievedChunk"


@pytest.mark.asyncio
async def test_retrieve_with_filters(
    mock_embedding_service: MagicMock,
    mock_vector_store: MagicMock,
) -> None:
    """Test retrieval with metadata filters."""
    retriever = SemanticRetriever(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
    )

    filters = {"ticker": "AAPL", "period": "2023"}
    await retriever.retrieve("test query", top_k=5, filters=filters)

    mock_vector_store.similarity_search.assert_called_once_with(
        query_vector=[0.1] * 1536,
        top_k=5,
        filters=filters,
    )


@pytest.mark.asyncio
async def test_retrieve_empty_query(
    mock_embedding_service: MagicMock,
    mock_vector_store: MagicMock,
) -> None:
    """Test retrieval with empty query handles errors from embedding service."""
    # Let's assume embedding service raises an error for empty query
    mock_embedding_service.embed_query.side_effect = ValueError("Empty query")

    retriever = SemanticRetriever(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
    )

    with pytest.raises(ValueError, match="Empty query"):
        await retriever.retrieve("")

    mock_vector_store.similarity_search.assert_not_called()


@pytest.fixture
def mock_keyword_retriever() -> MagicMock:
    """Mock KeywordRetriever."""
    retriever = MagicMock(spec=KeywordRetriever)
    retriever.retrieve = AsyncMock(return_value=[])
    return retriever


@pytest.fixture
def mock_semantic_retriever() -> MagicMock:
    """Mock SemanticRetriever."""
    retriever = MagicMock(spec=SemanticRetriever)
    retriever.retrieve = AsyncMock(return_value=[])
    return retriever


@pytest.mark.asyncio
async def test_keyword_retrieve_success(
    mock_vector_store: MagicMock,
) -> None:
    """Test KeywordRetriever successful retrieval."""
    mock_vector_store.keyword_search = AsyncMock(
        return_value=[
            SearchResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                content="Dummy keyword content",
                section_name="item_1",
                chunk_index=0,
                similarity=0.9,
                document_metadata={},
            )
        ]
    )

    retriever = KeywordRetriever(vector_store=mock_vector_store)
    results = await retriever.retrieve("test keyword", top_k=1)

    mock_vector_store.keyword_search.assert_called_once_with(
        query="test keyword",
        top_k=1,
        filters=None,
    )
    assert len(results) == 1
    assert results[0].content == "Dummy keyword content"


@pytest.mark.asyncio
async def test_hybrid_retrieve_success(
    mock_semantic_retriever: MagicMock,
    mock_keyword_retriever: MagicMock,
) -> None:
    """Test HybridRetriever combines and deduplicates results."""
    shared_id = uuid4()

    mock_semantic_retriever.retrieve.return_value = [
        RetrievedChunk(
            chunk_id=shared_id,
            document_id=uuid4(),
            content="Shared chunk",
            section_name="item_1",
            chunk_index=0,
            similarity=0.9,
            document_metadata={},
        ),
        RetrievedChunk(
            chunk_id=uuid4(),
            document_id=uuid4(),
            content="Semantic only",
            section_name="item_2",
            chunk_index=1,
            similarity=0.8,
            document_metadata={},
        ),
    ]

    mock_keyword_retriever.retrieve.return_value = [
        RetrievedChunk(
            chunk_id=shared_id,
            document_id=uuid4(),
            content="Shared chunk",
            section_name="item_1",
            chunk_index=0,
            similarity=0.95,
            document_metadata={},
        ),
        RetrievedChunk(
            chunk_id=uuid4(),
            document_id=uuid4(),
            content="Keyword only",
            section_name="item_3",
            chunk_index=2,
            similarity=0.85,
            document_metadata={},
        ),
    ]

    retriever = HybridRetriever(
        semantic_retriever=mock_semantic_retriever,
        keyword_retriever=mock_keyword_retriever,
    )

    results = await retriever.retrieve("test hybrid", top_k=5)

    assert len(results) == 3
    # First chunk should be the shared one from semantic retriever (due to interleaving)
    assert results[0].chunk_id == shared_id
    assert results[0].content == "Shared chunk"
