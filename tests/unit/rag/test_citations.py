"""Unit tests for citation extraction."""

import uuid

from src.rag.citations import extract_citations, format_answer_with_citations
from src.rag.models import RetrievedChunk


def test_extract_citations_success() -> None:
    """Verifies UUIDs and Document markers are correctly parsed via Regex."""
    doc_id1 = str(uuid.uuid4())
    doc_id2 = str(uuid.uuid4())
    text = (
        f"According to [Document {doc_id1}], the revenue increased. "
        f"Also mentioned in [Document {doc_id2}] and again [Document {doc_id1}]."
    )
    citations = extract_citations(text)

    assert len(citations) == 2
    assert citations[0] == doc_id1
    assert citations[1] == doc_id2


def test_extract_citations_no_citations() -> None:
    """Verifies the function handles text with no markers gracefully."""
    text = "This text has no citations at all. Just some [Random Tags]."
    citations = extract_citations(text)
    assert len(citations) == 0


def test_format_answer_with_citations() -> None:
    """Verifies format_answer_with_citations maps to chunks correctly."""
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    mock_chunk = RetrievedChunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        content="Test content",
        section_name="Test section",
        chunk_index=0,
        similarity=0.9,
        document_metadata={},
    )

    answer = f"According to [Document {doc_id}], it is true."
    result = format_answer_with_citations(answer, [mock_chunk])

    assert result["answer"] == answer
    assert len(result["citations"]) == 1
    assert result["citations"][0]["document_id"] == str(doc_id)
    assert result["citations"][0]["chunk_id"] == str(chunk_id)
