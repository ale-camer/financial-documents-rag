"""Section-aware document chunker for SEC 10-K financial filings."""

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.indexing.models import DocumentChunk
from src.ingestion.models import ParsedDocument


class SectionAwareChunker:
    """Section-aware chunker that respects SEC 10-K Item boundaries."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        encoding_name: str = "cl100k_base",
    ) -> None:
        """Initialize the chunker with tokenizer and text splitter settings."""
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative.")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding_name = encoding_name
        self.tokenizer = tiktoken.get_encoding(encoding_name)
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=self.count_tokens,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def count_tokens(self, text: str) -> int:
        """Calculate token count using the configured tiktoken tokenizer."""
        if not text or not text.strip():
            return 0
        return len(self.tokenizer.encode(text))

    def chunk_section(
        self,
        section_name: str,
        text: str,
        document_id: str | None = None,
        start_index: int = 0,
    ) -> list[DocumentChunk]:
        """Split a single section's text into chunks within token limits."""
        stripped = text.strip()
        if not stripped:
            return []

        raw_chunks = self.splitter.split_text(stripped)
        chunks: list[DocumentChunk] = []

        for i, chunk_text in enumerate(raw_chunks):
            token_cnt = self.count_tokens(chunk_text)
            chunks.append(
                DocumentChunk(
                    content=chunk_text,
                    section_name=section_name,
                    document_id=document_id,
                    chunk_index=start_index + i,
                    token_count=token_cnt,
                )
            )
        return chunks

    def chunk_document(
        self,
        document: ParsedDocument,
        document_id: str | None = None,
    ) -> list[DocumentChunk]:
        """Split a ParsedDocument preserving SEC section boundaries."""
        effective_doc_id = (
            document_id
            if document_id is not None
            else document.metadata.accession_number
        )
        all_chunks: list[DocumentChunk] = []
        current_index = 0

        for section in document.sections:
            section_chunks = self.chunk_section(
                section_name=section.section_name,
                text=section.raw_text,
                document_id=effective_doc_id,
                start_index=current_index,
            )
            all_chunks.extend(section_chunks)
            current_index += len(section_chunks)

        return all_chunks
