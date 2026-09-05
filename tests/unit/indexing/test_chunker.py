"""Unit tests for SectionAwareChunker and DocumentChunk model."""

import pytest
from pydantic import ValidationError

from src.indexing.chunker import SectionAwareChunker
from src.indexing.models import DocumentChunk
from src.ingestion.models import FilingMetadata, ParsedDocument, ParsedSection


@pytest.fixture
def chunker() -> SectionAwareChunker:
    """Provide a SectionAwareChunker instance with standard configuration."""
    return SectionAwareChunker(chunk_size=512, chunk_overlap=50)


@pytest.fixture
def sample_document() -> ParsedDocument:
    """Provide a sample ParsedDocument with multiple sections for testing."""
    metadata = FilingMetadata(
        cik="0000320193",
        ticker="AAPL",
        period="2023-09-30",
        accession_number="0000320193-23-000106",
        form_type="10-K",
    )
    sec_1 = ParsedSection(
        section_name="item_1",
        raw_text=(
            "Item 1. Business.\n\n"
            "Apple designs, manufactures and markets smartphones, "
            "personal computers, tablets, wearables and accessories, "
            "and sells a variety of related services. "
            "The Company's fiscal year is the 52 or 53-week period "
            "that ends on the last Saturday of September."
        ),
    )
    sec_1a = ParsedSection(
        section_name="item_1a",
        raw_text=(
            "Item 1A. Risk Factors.\n\n"
            "The Company's business, results of operations and financial "
            "condition can be adversely affected by global economic "
            "conditions, supply chain disruptions, and highly "
            "competitive markets across all product and service categories."
        ),
    )
    return ParsedDocument(metadata=metadata, sections=[sec_1, sec_1a])


def test_document_chunk_model_valid() -> None:
    """Verify DocumentChunk initialization with valid fields."""
    chunk = DocumentChunk(
        content="This is chunk text.",
        section_name="ITEM_1",
        document_id="doc-123",
        chunk_index=0,
        token_count=5,
    )
    assert chunk.content == "This is chunk text."
    assert chunk.section_name == "item_1"
    assert chunk.document_id == "doc-123"
    assert chunk.chunk_index == 0
    assert chunk.token_count == 5


def test_document_chunk_model_invalid_content() -> None:
    """Verify empty content raises ValidationError."""
    with pytest.raises(ValidationError, match="content cannot be empty"):
        DocumentChunk(
            content="   ",
            section_name="item_1",
            chunk_index=0,
            token_count=0,
        )


def test_document_chunk_model_invalid_section_name() -> None:
    """Verify empty section_name raises ValidationError."""
    with pytest.raises(ValidationError, match="section_name cannot be empty"):
        DocumentChunk(
            content="Valid content.",
            section_name="   ",
            chunk_index=0,
            token_count=3,
        )


def test_document_chunk_model_invalid_chunk_index() -> None:
    """Verify negative chunk_index raises ValidationError."""
    with pytest.raises(ValidationError, match="chunk_index"):
        DocumentChunk(
            content="Valid content.",
            section_name="item_1",
            chunk_index=-1,
            token_count=3,
        )


def test_document_chunk_model_invalid_token_count() -> None:
    """Verify negative token_count raises ValidationError."""
    with pytest.raises(ValidationError, match="token_count"):
        DocumentChunk(
            content="Valid content.",
            section_name="item_1",
            chunk_index=0,
            token_count=-5,
        )


def test_chunker_invalid_init_parameters() -> None:
    """Verify ValueError is raised for invalid chunker parameters."""
    with pytest.raises(ValueError, match="chunk_size must be positive"):
        SectionAwareChunker(chunk_size=0)

    with pytest.raises(ValueError, match="chunk_overlap must be non-negative"):
        SectionAwareChunker(chunk_size=512, chunk_overlap=-1)

    with pytest.raises(ValueError, match="strictly less than chunk_size"):
        SectionAwareChunker(chunk_size=100, chunk_overlap=100)

    with pytest.raises(ValueError, match="strictly less than chunk_size"):
        SectionAwareChunker(chunk_size=100, chunk_overlap=150)


def test_count_tokens_accuracy(chunker: SectionAwareChunker) -> None:
    """Verify token counting accuracy and empty string handling."""
    assert chunker.count_tokens("") == 0
    assert chunker.count_tokens("   ") == 0

    token_cnt = chunker.count_tokens("Hello world from financial documents RAG.")
    assert token_cnt > 0
    assert isinstance(token_cnt, int)


def test_chunk_single_section_under_limit(chunker: SectionAwareChunker) -> None:
    """Verify text shorter than chunk_size produces a single chunk."""
    text = "Short section content that is well within the 512 token boundary."
    chunks = chunker.chunk_section("item_1", text, document_id="doc-1")

    assert len(chunks) == 1
    assert chunks[0].content == text
    assert chunks[0].section_name == "item_1"
    assert chunks[0].document_id == "doc-1"
    assert chunks[0].chunk_index == 0
    assert chunks[0].token_count <= 512


def test_chunk_single_section_over_limit() -> None:
    """Verify text exceeding chunk_size is split into multiple small chunks."""
    chunker = SectionAwareChunker(chunk_size=50, chunk_overlap=10)
    paragraph = (
        "Financial technology continues to evolve rapidly across "
        "institutional markets. Automated processing pipelines, "
        "machine learning models, and dense vector retrieval systems "
        "are transforming how analysts interact with SEC filings. "
        "By structuring documents hierarchically, systems maintain "
        "context and integrity."
    )

    long_text = "\n\n".join([paragraph] * 8)

    chunks = chunker.chunk_section("item_7", long_text, document_id="doc-7")

    assert len(chunks) > 1
    for i, chunk in enumerate(chunks):
        assert chunk.section_name == "item_7"
        assert chunk.document_id == "doc-7"
        assert chunk.chunk_index == i
        assert chunk.token_count <= 50


def test_chunk_overlap_preservation() -> None:
    """Verify consecutive chunks preserve overlap text across boundaries."""
    chunker = SectionAwareChunker(chunk_size=30, chunk_overlap=10)
    text = (
        "Sentence one discusses alpha and beta. "
        "Sentence two discusses gamma and delta. "
        "Sentence three discusses epsilon and zeta. "
        "Sentence four discusses eta and theta. "
        "Sentence five discusses iota and kappa."
    )
    chunks = chunker.chunk_section("item_1", text)

    assert len(chunks) >= 2
    words_chunk_0 = set(chunks[0].content.split())
    words_chunk_1 = set(chunks[1].content.split())
    assert len(words_chunk_0.intersection(words_chunk_1)) > 0


def test_chunk_preserves_section_boundary(
    chunker: SectionAwareChunker, sample_document: ParsedDocument
) -> None:
    """Verify chunks from different sections are never combined together."""
    chunks = chunker.chunk_document(sample_document)

    item_1_chunks = [c for c in chunks if c.section_name == "item_1"]
    item_1a_chunks = [c for c in chunks if c.section_name == "item_1a"]

    assert len(item_1_chunks) > 0
    assert len(item_1a_chunks) > 0
    assert len(chunks) == len(item_1_chunks) + len(item_1a_chunks)

    # Item 1 content must not appear in any Item 1A chunk, and vice versa
    for chunk in item_1_chunks:
        assert "Risk Factors" not in chunk.content
    for chunk in item_1a_chunks:
        assert "Apple designs, manufactures" not in chunk.content


def test_chunk_document_sequential_indexing(
    chunker: SectionAwareChunker, sample_document: ParsedDocument
) -> None:
    """Verify chunk_index increments sequentially across all document sections."""
    chunks = chunker.chunk_document(sample_document)

    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_chunk_document_metadata_propagation(
    chunker: SectionAwareChunker, sample_document: ParsedDocument
) -> None:
    """Verify metadata is propagated to all chunks from document."""
    # Test default document_id from metadata accession number
    chunks_default = chunker.chunk_document(sample_document)
    expected_acc = sample_document.metadata.accession_number
    for chunk in chunks_default:
        assert chunk.document_id == expected_acc

    # Test explicit document_id override
    chunks_custom = chunker.chunk_document(sample_document, document_id="custom-uuid")
    for chunk in chunks_custom:
        assert chunk.document_id == "custom-uuid"


def test_chunk_empty_section_ignored(chunker: SectionAwareChunker) -> None:
    """Verify empty or whitespace-only sections produce no chunks."""
    assert chunker.chunk_section("item_1", "") == []
    assert chunker.chunk_section("item_1", "   \n\t  ") == []


def test_chunk_empty_document(chunker: SectionAwareChunker) -> None:
    """Verify ParsedDocument with no sections produces no chunks."""
    meta = FilingMetadata(
        cik="0000320193",
        period="2023-09-30",
        accession_number="0000320193-23-000106",
    )
    empty_doc = ParsedDocument(metadata=meta, sections=[])
    assert chunker.chunk_document(empty_doc) == []


def test_chunk_custom_size_and_overlap() -> None:
    """Verify custom chunk_size and chunk_overlap are respected."""
    chunker = SectionAwareChunker(chunk_size=100, chunk_overlap=20)
    assert chunker.chunk_size == 100
    assert chunker.chunk_overlap == 20
    assert chunker.encoding_name == "cl100k_base"
