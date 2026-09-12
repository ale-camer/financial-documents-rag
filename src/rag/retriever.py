"""Semantic retrieval layer using pgvector HNSW."""

from typing import Any

from src.indexing.embeddings import EmbeddingService
from src.rag.models import RetrievedChunk
from src.storage.vector_store import VectorStoreClient


class SemanticRetriever:
    """Retriever for finding semantically similar document chunks."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreClient,
    ) -> None:
        """Initialize with embedding service and vector store client."""
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Embed a query and return top-k most similar document chunks."""
        # 1. Embed the query
        query_vector = await self.embedding_service.embed_query(query)

        # 2. Query the vector store
        results = await self.vector_store.similarity_search(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters,
        )

        # 3. Map SearchResult to RetrievedChunk
        retrieved_chunks = []
        for result in results:
            chunk = RetrievedChunk(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                content=result.content,
                section_name=result.section_name,
                chunk_index=result.chunk_index,
                similarity=result.similarity,
                document_metadata=result.document_metadata,
            )
            retrieved_chunks.append(chunk)

        return retrieved_chunks


class KeywordRetriever:
    """Retriever for finding document chunks using BM25 keyword search."""

    def __init__(self, vector_store: VectorStoreClient) -> None:
        """Initialize with vector store client."""
        self.vector_store = vector_store

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Perform keyword search and return top-k document chunks."""
        results = await self.vector_store.keyword_search(
            query=query,
            top_k=top_k,
            filters=filters,
        )

        retrieved_chunks = []
        for result in results:
            chunk = RetrievedChunk(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                content=result.content,
                section_name=result.section_name,
                chunk_index=result.chunk_index,
                similarity=result.similarity,
                document_metadata=result.document_metadata,
            )
            retrieved_chunks.append(chunk)

        return retrieved_chunks


class HybridRetriever:
    """Retriever combining semantic and keyword search results."""

    def __init__(
        self,
        semantic_retriever: SemanticRetriever,
        keyword_retriever: KeywordRetriever,
    ) -> None:
        """Initialize with semantic and keyword retrievers."""
        self.semantic_retriever = semantic_retriever
        self.keyword_retriever = keyword_retriever

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Combine semantic and keyword search, deduplicate and re-rank."""
        import asyncio

        semantic_task = self.semantic_retriever.retrieve(query, top_k, filters)
        keyword_task = self.keyword_retriever.retrieve(query, top_k, filters)

        semantic_results, keyword_results = await asyncio.gather(
            semantic_task, keyword_task
        )

        seen_chunks = set()
        combined_results = []

        max_len = max(len(semantic_results), len(keyword_results))
        for i in range(max_len):
            if i < len(semantic_results):
                chunk = semantic_results[i]
                if chunk.chunk_id not in seen_chunks:
                    seen_chunks.add(chunk.chunk_id)
                    combined_results.append(chunk)

            if i < len(keyword_results):
                chunk = keyword_results[i]
                if chunk.chunk_id not in seen_chunks:
                    seen_chunks.add(chunk.chunk_id)
                    combined_results.append(chunk)

        return combined_results[:top_k]
