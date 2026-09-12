"""Citation extraction and formatting utilities for RAG outputs."""

import re
from typing import Any
from uuid import UUID

from src.rag.models import RetrievedChunk


def extract_citations(text: str) -> list[str]:
    """
    Extract document UUID citations from generated text.

    Matches formats like [Document <UUID>].
    """
    pattern = (
        r"\[Document\s+([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\]"
    )
    matches = re.findall(pattern, text)

    unique_matches: list[str] = []
    for m in matches:
        if m not in unique_matches:
            unique_matches.append(m)
    return unique_matches


def format_answer_with_citations(
    answer: str, chunks: list[RetrievedChunk]
) -> dict[str, Any]:
    """
    Process the answer, extract citations, and map them to the original chunks.
    """
    cited_ids = extract_citations(answer)

    citations: list[dict[str, Any]] = []
    for doc_id_str in cited_ids:
        try:
            doc_uuid = UUID(doc_id_str)
        except ValueError:
            continue

        matching_chunks = [c for c in chunks if c.document_id == doc_uuid]

        for chunk in matching_chunks:
            citations.append(
                {
                    "document_id": str(chunk.document_id),
                    "chunk_id": str(chunk.chunk_id),
                    "section_name": chunk.section_name,
                    "text": chunk.content,
                    "similarity": chunk.similarity,
                }
            )

    unique_citations: list[dict[str, Any]] = []
    seen = set()
    for citation in citations:
        if citation["chunk_id"] not in seen:
            seen.add(citation["chunk_id"])
            unique_citations.append(citation)

    return {"answer": answer, "citations": unique_citations}
