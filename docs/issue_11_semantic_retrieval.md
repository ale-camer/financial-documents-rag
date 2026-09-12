# Workflow and Specification: Issue 11 — Implement semantic similarity search with HNSW index on pgvector

**Milestone**: M3: Hybrid Retrieval & RAG Generation Pipeline  
**GitHub Issue**: #11  
**Branch**: `feature/issue-11-semantic-retrieval`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-11-semantic-retrieval
```

---

## 2. Development (files in `src/rag/`)

### 2.1 Domain Models: `src/rag/models.py`
Define models for the RAG retrieval pipeline:

- **`RetrievedChunk`**:
  - Should inherit from or alias `SearchResult` (from `src.storage.models`) to include fields: `chunk_id`, `document_id`, `content`, `section_name`, `chunk_index`, `similarity`, and `document_metadata`.

### 2.2 Semantic Retriever: `src/rag/retriever.py`
Implement `SemanticRetriever` to orchestrate query embedding and vector search:

- **Initialization**:
  - `__init__(self, embedding_service: EmbeddingService, vector_store: VectorStoreClient)`

- **Methods**:
  - `async def retrieve(self, query: str, top_k: int = 5, filters: dict[str, Any] | None = None) -> list[RetrievedChunk]:`
    - **Step 1:** Call `await self.embedding_service.embed_query(query)` to get the dense vector for the query.
    - **Step 2:** Call `await self.vector_store.similarity_search(...)` passing the `query_vector`, `top_k`, and optional `filters`.
    - **Step 3:** Convert or cast the returned `SearchResult` objects into `RetrievedChunk` instances and return them.

### 2.3 Package Exports: `src/rag/__init__.py`
Export `SemanticRetriever` and `RetrievedChunk`.

---

## 3. Testing (`tests/unit/rag/`)

### 3.1 Unit Testing (Mocked dependencies)

#### File structure:
```
tests/unit/rag/
└── test_retriever.py
```

| Test | Verifies |
|---|---|
| `test_retrieve_success` | Verifies `embed_query` and `similarity_search` are called with correct arguments and results mapped properly. |
| `test_retrieve_with_filters` | Verifies metadata filters (`ticker`, `period`, `section_name`) are propagated to the vector store. |
| `test_retrieve_empty_query` | Verifies behavior when an empty query string is provided (should it raise an error via `EmbeddingService`?). |

### Execution commands:

```bash
# Run unit tests
pytest tests/unit/rag/test_retriever.py -v
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
git add src/rag/ tests/unit/rag/ docs/issue_11_semantic_retrieval.md
git commit -m "feat(rag): implement semantic retriever with pgvector (#11)"

# Push branch
git push -u origin feature/issue-11-semantic-retrieval

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(rag): implement semantic retriever with pgvector (#11)" \
  --body "Closes #11.
- Added \`RetrievedChunk\` model for the RAG pipeline.
- Implemented \`SemanticRetriever\` orchestrating query embedding and pgvector search.
- Added support for metadata filtering in retrieval.
- Added unit tests with mocked \`EmbeddingService\` and \`VectorStoreClient\`."
```

---

## Closing Criteria

- [ ] `SemanticRetriever` correctly fetches and maps search results.
- [ ] Unit tests pass with mocked dependencies.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #11`.
