"""Indexing pipeline orchestrating chunker, embeddings, and vector store."""

import asyncio
from uuid import UUID

from tqdm.asyncio import tqdm

from src.indexing.chunker import SectionAwareChunker
from src.indexing.embeddings import EmbeddingService
from src.indexing.models import DocumentChunk
from src.ingestion.models import ParsedDocument
from src.storage.vector_store import VectorStoreClient


class IndexingPipeline:
    """Orchestrates chunking, embedding, and storage of SEC documents."""

    def __init__(
        self,
        chunker: SectionAwareChunker,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreClient,
    ) -> None:
        """Initialize the pipeline with its required components."""
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    async def process_document(
        self,
        document: ParsedDocument,
        batch_size: int = 100,
        concurrency: int = 5,
        show_progress: bool = True,
    ) -> None:
        """Process a document end-to-end and store in vector database."""
        # 1. Upsert document
        doc_id = await self.vector_store.upsert_document(document.metadata)

        # 2. Chunk document
        chunks = self.chunker.chunk_document(document, document_id=str(doc_id))

        if not chunks:
            return

        # 3. Upsert chunks to get their IDs
        chunk_ids = await self.vector_store.upsert_chunks(doc_id, chunks)

        # 4. Batch chunks and IDs
        batches = []
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i : i + batch_size]
            batch_ids = chunk_ids[i : i + batch_size]
            batches.append((batch_ids, batch_chunks))

        # 5. Define asynchronous task for each batch with a semaphore
        semaphore = asyncio.Semaphore(concurrency)

        async def _process_batch(
            b_ids: list[UUID], b_chunks: list[DocumentChunk]
        ) -> None:
            async with semaphore:
                embeddings = await self.embedding_service.embed_chunks(b_chunks)
                await self.vector_store.upsert_embeddings(b_ids, embeddings)

        tasks = [_process_batch(b_ids, b_chunks) for b_ids, b_chunks in batches]

        # 6 & 7. Execute tasks, optionally with a progress bar
        if show_progress:
            await tqdm.gather(*tasks, desc="Embedding batches")
        else:
            await asyncio.gather(*tasks)
