# Workflow and Specification: Issue 12 — Add BM25 keyword search layer for hybrid retrieval

**Milestone**: M3: Hybrid Retrieval & RAG Generation Pipeline  
**GitHub Issue**: #12  
**Branch**: `feature/issue-12-bm25-retrieval`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-12-bm25-retrieval
```

---

## 2. Development

### 2.1 Database Schema Updates (`src/storage/schema.sql` or equivalent)
Update the database schema to support full-text search:
- Add a `content_tsvector` column to the `chunks` table if it doesn't already exist.
- Create a GIN index on `chunks.content_tsvector` to optimize keyword search performance.
- Update insertion logic (e.g., triggers or `VectorStoreClient.upsert_chunks`) to populate `content_tsvector` using `to_tsvector('english', content)`.

### 2.2 Vector Store Client Updates (`src/storage/vector_store.py`)
Add keyword search capabilities to the storage layer:

- **Methods**:
  - `async def keyword_search(self, query: str, top_k: int = 5, filters: dict[str, Any] | None = None) -> list[SearchResult]:`
    - **Step 1:** Construct a SQL query using `plainto_tsquery('english', %s)` or `to_tsquery` to support multi-term searches.
    - **Step 2:** Use `ts_rank` to score results against the `content_tsvector` column.
    - **Step 3:** Apply metadata filters (ticker, period, etc.) identical to `similarity_search`.
    - **Step 4:** Execute the query, parse the results, and return a list of `SearchResult` instances. The `similarity` field should be mapped to the `ts_rank` score.

### 2.3 Keyword Retriever (`src/rag/retriever.py` or `src/rag/keyword_retriever.py`)
Implement the `KeywordRetriever` class:

- **Initialization**:
  - `__init__(self, vector_store: VectorStoreClient)`

- **Methods**:
  - `async def retrieve(self, query: str, top_k: int = 5, filters: dict[str, Any] | None = None) -> list[RetrievedChunk]:`
    - Call `await self.vector_store.keyword_search(query, top_k, filters)`.
    - Convert `SearchResult` items into `RetrievedChunk` instances and return them.

### 2.4 Hybrid Retriever (`src/rag/retriever.py` or `src/rag/hybrid_retriever.py`)
Implement a `HybridRetriever` to combine semantic and keyword searches:

- **Initialization**:
  - `__init__(self, semantic_retriever: SemanticRetriever, keyword_retriever: KeywordRetriever)`

- **Methods**:
  - `async def retrieve(self, query: str, top_k: int = 5, filters: dict[str, Any] | None = None) -> list[RetrievedChunk]:`
    - Execute both retrievers concurrently (e.g., using `asyncio.gather`).
    - Combine the results (keyword results ∪ semantic results).
    - Deduplicate the results based on `chunk_id`.
    - Apply a Reciprocal Rank Fusion (RRF) or simple ranking heuristic to re-score and sort the combined results.
    - Return the top `top_k` deduplicated chunks.

---

## 3. Testing (`tests/unit/rag/` and `tests/unit/storage/`)

### 3.1 Unit Testing

| Test | Verifies |
|---|---|
| `test_keyword_retrieve_success` | Verifies `KeywordRetriever.retrieve` correctly calls the vector store and maps results to `RetrievedChunk`. |
| `test_vector_store_keyword_search` | Verifies SQL generation uses `plainto_tsquery` and handles filters correctly. |
| `test_hybrid_retriever_deduplication` | Verifies that combining keyword and semantic results removes duplicates based on `chunk_id`. |
| `test_hybrid_retriever_ranking` | Verifies that the hybrid retriever returns appropriately sorted results up to `top_k`. |

### Execution commands:

```bash
# Run unit tests
pytest tests/unit/rag/ -v
pytest tests/unit/storage/ -v
```

---

## 4. Code Quality

```bash
make format      # Auto-format with ruff
make lint        # ruff linter
make type-check  # strict mypy
make check       # lint + type-check combined
```

---

## 5. Push to GitHub and Close

```bash
# Commit changes
git add src/ tests/ docs/issue_12_bm25_retrieval.md
git commit -m "feat(rag): add BM25 keyword search layer for hybrid retrieval (#12)"

# Push branch
git push -u origin feature/issue-12-bm25-retrieval

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(rag): add BM25 keyword search layer for hybrid retrieval (#12)" \
  --body "Closes #12.
- Added \`content_tsvector\` GIN index for BM25 keyword retrieval.
- Implemented \`keyword_search\` in \`VectorStoreClient\` using \`ts_rank\` and \`to_tsquery\`.
- Implemented \`KeywordRetriever\` and \`HybridRetriever\` for semantic + keyword search union.
- Ensured hybrid search deduplicates results by \`chunk_id\`.
- Added unit tests validating the ranking and deduplication behavior."
```

---

## Closing Criteria

- [ ] `KeywordRetriever` uses PostgreSQL `tsvector` full-text search on chunk content.
- [ ] GIN index is created on `chunks.content_tsvector` column.
- [ ] Multi-term queries are supported using `to_tsquery` / `plainto_tsquery`.
- [ ] Returned scored results are compatible with the semantic retrieval output format (`SearchResult` / `RetrievedChunk`).
- [ ] Hybrid retrieval returns keyword results ∪ semantic results, deduplicated by `chunk_id`.
- [ ] Unit tests validate ranking and deduplication behavior.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #12`.
