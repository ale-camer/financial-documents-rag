-- Migration 001 Rollback: Drop embeddings, chunks, documents tables

DROP INDEX IF EXISTS idx_embeddings_hnsw;
DROP TABLE IF EXISTS embeddings CASCADE;
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
