-- Migration 001: Initial pgvector schema for financial documents RAG system
-- Description: Creates documents, chunks, and embeddings tables with HNSW index

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cik VARCHAR(10) NOT NULL,
    ticker VARCHAR(10),
    period VARCHAR(20) NOT NULL,
    form_type VARCHAR(10) NOT NULL DEFAULT '10-K',
    accession_number VARCHAR(25) NOT NULL UNIQUE,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_cik ON documents(cik);
CREATE INDEX IF NOT EXISTS idx_documents_ticker ON documents(ticker);
CREATE INDEX IF NOT EXISTS idx_documents_accession_number ON documents(accession_number);

-- Table: chunks
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_name VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL CHECK (token_count >= 0),
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_chunks_document_chunk_index UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_section_name ON chunks(section_name);

-- Table: embeddings
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE UNIQUE,
    embedding vector(1536) NOT NULL,
    model_name VARCHAR(50) NOT NULL DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_id ON embeddings(chunk_id);

-- HNSW vector similarity search index (using cosine distance)
CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON embeddings 
USING hnsw (embedding vector_cosine_ops);
