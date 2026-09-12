"""Domain models for RAG pipeline."""

from src.storage.models import SearchResult


class RetrievedChunk(SearchResult):
    """A semantic search result retrieved from the vector store."""

    pass
