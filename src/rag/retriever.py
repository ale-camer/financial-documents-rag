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
