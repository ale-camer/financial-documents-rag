"""RAG orchestration pipeline linking retrieval and generation."""

from typing import Any

from src.rag.generator import RAGGenerator
from src.rag.retriever import HybridRetriever


class RAGPipeline:
    """Orchestrates document retrieval and answer generation."""

    def __init__(self, retriever: HybridRetriever, generator: RAGGenerator) -> None:
        """Initialize pipeline with a retriever and generator."""
        self.retriever = retriever
        self.generator = generator

    async def ask(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Retrieve context and generate an answer."""
        chunks = await self.retriever.retrieve(query, filters=filters)
        answer = await self.generator.generate_answer(query, chunks)

        return {
            "answer": answer,
            "source_documents": chunks,
        }
