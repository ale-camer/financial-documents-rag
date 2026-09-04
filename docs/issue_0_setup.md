# Issue 0 — Day 0 Setup & Scaffolding

**Project**: P-07 Financial Documents RAG System
**Branch**: `feature/day-0-setup`
**Milestone**: (Pre-M1 scaffold — no milestone assigned)
**Status**: 🔄 In Progress

---

## Day 0 Checklist

### Git & Repository

- [x] `git init` with `main` as default branch
- [x] Initial empty commit on `main`
- [x] `develop` branch created from `main`
- [x] `feature/day-0-setup` branch created from `develop`
- [ ] GitHub repository created (`financial-documents-rag`, public)
- [ ] `main` and `develop` pushed to remote
- [ ] `feature/day-0-setup` pushed to remote

### Virtual Environment

- [x] `.venv` created with `python3 -m venv .venv`
- [x] Dev dependencies installed (`pytest`, `ruff`, `mypy`)

### Configuration Files

- [x] `.gitignore`
- [x] `.env.example`
- [x] `pyproject.toml` (hatchling + ruff + mypy + pytest config)
- [x] `Makefile` (install, test, lint, format, type-check, up, down)
- [x] `docker-compose.yml` (PostgreSQL 16 + pgvector)

### Directory Structure

- [x] `src/ingestion/` (SEC EDGAR client, 10-K parsers)
- [x] `src/indexing/` (chunkers, embedding pipelines)
- [x] `src/storage/` (pgvector schema, vector store client)
- [x] `src/rag/` (retrieval chains, LangChain prompts, generator)
- [x] `src/api/` (FastAPI endpoints, routers, schemas)
- [x] `tests/unit/`
- [x] `tests/integration/`
- [x] `docs/`

### Documentation

- [x] `README.md` (problem statement, architecture, stack, quickstart)
- [x] `docs/issue_0_setup.md` (this file)

### GitHub Setup

- [ ] Repository created as public
- [ ] 5 Milestones created (M1–M5)
- [ ] 25 atomic issues created and assigned to milestones

---

## Architectural Decision Records (ADRs)

### ADR-001: Why pgvector over Pinecone / Weaviate

**Decision**: Use PostgreSQL + pgvector for vector storage.

**Context**: We need persistent, transactional storage for both document metadata
and their corresponding embeddings. A dedicated vector database would require
a separate operational dependency.

**Reasoning**:
- Single database for relational data (documents, chunks) AND vectors → simpler operations
- pgvector's HNSW index delivers sub-millisecond ANN search at our scale
- Familiar SQL query interface for hybrid retrieval (BM25 via `tsvector` + vector similarity)
- No additional managed service cost for early-stage development

**Trade-off**: At very large scale (100M+ vectors), Pinecone or Weaviate offer
better horizontal scaling. This is acceptable for the current scope.

---

### ADR-002: Why LangChain for RAG Orchestration

**Decision**: Use LangChain 0.3 as the RAG orchestration framework.

**Context**: We need to compose retrieval, prompt construction, LLM calls, and
citation extraction into a coherent pipeline.

**Reasoning**:
- Rich ecosystem of retrievers, document loaders, and chain primitives
- Native streaming support via `astream()` for FastAPI SSE endpoints
- Pluggable LLM backends (OpenAI, Anthropic, local models) via unified interface
- LCEL (LangChain Expression Language) enables composable, debuggable chains

**Trade-off**: LangChain adds abstraction overhead. If requirements simplify,
direct OpenAI SDK calls may be preferred.

---

### ADR-003: Section-Aware Chunking Strategy for 10-K Filings

**Decision**: Chunk 10-K documents by SEC section boundaries, not by fixed
token count.

**Context**: 10-K filings have well-defined sections (Items 1–15). Naive
fixed-size chunking often splits across section boundaries, mixing context
from different topics (e.g., Risk Factors bleeding into Business Description).

**Reasoning**:
- Each chunk stays within its semantic domain (e.g., "Risk Factors" = Item 1A)
- Citations can reference the exact Item and page range
- Retrieval precision improves: a question about liquidity retrieves chunks
  from Item 7 (MD&A), not from Item 1 (Business)
- Secondary chunking within sections uses sentence-boundary-aware splitter
  (e.g., `RecursiveCharacterTextSplitter` with `\n\n` → `\n` → ` ` hierarchy)

**Index strategy**:
- **HNSW** over **IVFFlat**: HNSW doesn't require knowing N (total vectors)
  upfront, delivers consistent recall at query time, and has O(log N) insert
  complexity. IVFFlat requires a training phase and degrades if the corpus
  grows significantly after index creation.

---

## Milestones Summary

| ID | Title | Issues |
|----|-------|--------|
| M1 | SEC EDGAR Ingestion & Document Parsing | #1–#5 |
| M2 | Semantic Chunking, Embeddings & pgvector Storage | #6–#10 |
| M3 | Hybrid Retrieval & RAG Generation Pipeline | #11–#15 |
| M4 | FastAPI Service, Citation Layer & Evaluation | #16–#20 |
| M5 | CI/CD, Observability & Containerized Deployment | #21–#25 |

---

## Closing Criteria

This issue is closed when:

1. All checklist items above are marked `[x]`
2. `feature/day-0-setup` is merged to `develop` via PR
3. All 5 milestones and 25 issues exist on GitHub
4. `make install` runs without errors
5. `docker-compose config` validates without errors
