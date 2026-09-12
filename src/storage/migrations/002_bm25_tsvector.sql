-- Migration 002: Add content_tsvector for BM25 keyword search
-- Description: Adds a generated tsvector column for chunk content and a GIN index

ALTER TABLE chunks 
ADD COLUMN IF NOT EXISTS content_tsvector tsvector 
GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX IF NOT EXISTS idx_chunks_content_tsvector ON chunks USING GIN (content_tsvector);
