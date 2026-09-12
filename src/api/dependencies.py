"""Dependency injection for FastAPI endpoints."""

from functools import lru_cache

from src.indexing.embeddings import EmbeddingService
from src.rag.generator import RAGGenerator
from src.rag.pipeline import RAGPipeline
from src.rag.retriever import HybridRetriever, KeywordRetriever, SemanticRetriever
from src.storage.vector_store import VectorStoreClient


@lru_cache
def get_vector_store() -> VectorStoreClient:
    """Return a singleton instance of the vector store client."""
    return VectorStoreClient()


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Return a singleton instance of the embedding service."""
    return EmbeddingService()


@lru_cache
def get_hybrid_retriever() -> HybridRetriever:
    """Return a singleton instance of the hybrid retriever."""
    vs = get_vector_store()
    emb = get_embedding_service()
    semantic = SemanticRetriever(embedding_service=emb, vector_store=vs)
    keyword = KeywordRetriever(vector_store=vs)
    return HybridRetriever(semantic_retriever=semantic, keyword_retriever=keyword)


@lru_cache
def get_rag_generator() -> RAGGenerator:
    """Return a singleton instance of the RAG generator."""
    return RAGGenerator()


@lru_cache
def get_rag_pipeline() -> RAGPipeline:
    """Return a singleton instance of the RAG pipeline."""
    return RAGPipeline(
        retriever=get_hybrid_retriever(),
        generator=get_rag_generator(),
    )
