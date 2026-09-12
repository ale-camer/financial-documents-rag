# Financial Documents RAG System

> **P-07** — Part of the Financial Markets Intelligence Platform (DE → MLOps → AI Engineering)

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)](https://www.postgresql.org)
[![pgvector](https://img.shields.io/badge/pgvector-0.7-green)](https://github.com/pgvector/pgvector)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-purple)](https://python.langchain.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-teal?logo=fastapi)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Problem Statement

SEC 10-K annual filings are dense, lengthy documents (often 200+ pages) containing critical financial
information — risk factors, MD&A, financial statements. Manually extracting insights is slow and error-prone.

This system provides a **production-grade RAG (Retrieval-Augmented Generation)** pipeline that:
- Ingests 10-K filings directly from the **SEC EDGAR API**
- Chunks documents **section-aware** (preserving Item 1, 7, 7A, 8 boundaries)
- Stores dense vector embeddings in **PostgreSQL + pgvector** with HNSW indexing
- Answers natural language questions with **verifiable citations** from the source filing
- Exposes a clean **FastAPI** REST interface with streaming support

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Financial Documents RAG                     │
└─────────────────────────────────────────────────────────────────┘

  SEC EDGAR API
       │
       ▼
  ┌──────────────┐     ┌───────────────┐     ┌────────────────────┐
  │  Ingestion   │────▶│   Indexing    │────▶│  Storage           │
  │  - EDGAR     │     │  - Chunker    │     │  - PostgreSQL 16   │
  │    client    │     │    (section   │     │  - pgvector        │
  │  - 10-K      │     │    -aware)    │     │    (HNSW index)    │
  │    parser    │     │  - Embeddings │     │                    │
  └──────────────┘     └───────────────┘     └────────────────────┘
                                                      │
                                                      ▼
  ┌──────────────┐     ┌───────────────┐     ┌────────────────────┐
  │  FastAPI     │◀────│  RAG Pipeline │◀────│  Retrieval         │
  │  - /query    │     │  - LangChain  │     │  - Semantic search │
  │  - /ingest   │     │    chain      │     │  - BM25 keyword    │
  │  - /health   │     │  - Citation   │     │  - Hybrid rerank   │
  └──────────────┘     │    layer      │     └────────────────────┘
                       └───────────────┘
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Vector DB | PostgreSQL 16 + pgvector | Store and search dense embeddings |
| Indexing | HNSW (pgvector) | Approximate nearest-neighbor search |
| Embeddings | OpenAI `text-embedding-3-small` | 1536-dim dense vectors |
| Orchestration | LangChain 0.3 | RAG chain, prompts, retrieval |
| LLM | OpenAI GPT-4o-mini | Answer generation |
| API | FastAPI | REST endpoints with OpenAPI docs |
| Data source | SEC EDGAR API | 10-K filing downloads |
| Containerization | Docker + docker-compose | Local dev + production deployment |
| CI/CD | GitHub Actions | Automated test + lint pipeline |

## Quickstart

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- An OpenAI API key

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/ale-camer/financial-documents-rag.git
cd financial-documents-rag

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Start PostgreSQL + pgvector
make up

# 4. Create virtual environment and install dependencies
make install

# 5. Activate virtual environment
source .venv/bin/activate
```

### Running the API

```bash
# Start the FastAPI server (available after M4)
uvicorn src.api.main:app --reload
```

API docs available at: `http://localhost:8000/docs`

## Project Status

| Milestone | Status |
|-----------|--------|
| M1: SEC EDGAR Ingestion & Document Parsing | 🔲 Planned |
| M2: Semantic Chunking, Embeddings & pgvector Storage | 🔲 Planned |
| M3: Hybrid Retrieval & RAG Generation Pipeline | 🔲 Planned |
| M4: FastAPI Service, Citation Layer & Evaluation | ✅ Completed |
| M5: CI/CD, Observability & Containerized Deployment | 🔲 Planned |

## Repository Structure

```
financial-documents-rag/
├── src/
│   ├── ingestion/    # SEC EDGAR client and 10-K parsers
│   ├── indexing/     # Semantic chunkers and embedding pipelines
│   ├── storage/      # pgvector schema and vector store client
│   ├── rag/          # LangChain retrieval chains and prompts
│   └── api/          # FastAPI routers, schemas, endpoints
├── tests/
│   ├── unit/
│   └── integration/
├── docs/             # ADRs, issue tracking, architecture docs
├── docker-compose.yml
├── pyproject.toml
└── Makefile
```

## License

MIT License — see [LICENSE](LICENSE) for details.
