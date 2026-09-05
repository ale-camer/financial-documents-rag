# Workflow and Specification: Issue 9 — Build Vector Store Client (CRUD Operations on pgvector)

**Milestone**: M2: Semantic Chunking, Embeddings & pgvector Storage  
**GitHub Issue**: #9  
**Branch**: `feature/issue-9-vector-store-client`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-9-vector-store-client
```

---

## 2. Configure Dependencies

### 2.1 Dependencies in `pyproject.toml`

Add connection pool support (`psycopg_pool`) by updating the `psycopg` entry in [`pyproject.toml`](../pyproject.toml):

```diff
 dependencies = [
     "httpx>=0.27.0",
     "beautifulsoup4>=4.12.0",
     "lxml>=5.2.0",
     "pydantic>=2.7.0",
-    "psycopg[binary]>=3.1.18",
+    "psycopg[binary,pool]>=3.1.18",
     "pgvector>=0.3.0",
     "langchain-text-splitters>=0.3.0",
     "tiktoken>=0.7.0",
     "openai>=1.30.0",
 ]
```

### 2.2 Install into the virtual environment

Activate your `.venv` and install the updated dependencies:

```bash
# Activate virtual environment
source .venv/bin/activate

# Install updated dependencies in editable mode
pip install -e ".[dev]"
```

### 2.3 Verification

```bash
# Verify psycopg_pool and pgvector are available
python -c "import psycopg_pool; import pgvector; print('psycopg_pool & pgvector OK')"
```

---

## 3. Development (files in `src/storage/`)

### 3.1 Domain Models: `src/storage/models.py`
Define models for query results and vector store operations:

- **`SearchResult(BaseModel)`**:
  - `chunk_id: UUID`: Unique ID of the chunk.
  - `document_id: UUID`: ID of the associated filing document.
  - `content: str`: Text content of the chunk.
  - `section_name: str`: SEC section (e.g. `item_1`, `item_7`).
  - `chunk_index: int`: Index of the chunk within the document.
  - `similarity: float`: Cosine similarity score in range $[0, 1]$ computed as `1 - cosine_distance`.
  - `document_metadata: dict[str, Any]`: Document metadata (`cik`, `ticker`, `period`, `form_type`, `accession_number`).

### 3.2 Custom Exceptions: `src/storage/exceptions.py`
Define storage and vector store exceptions:

- **`StorageError(Exception)`**: Base exception for storage operations.
- **`VectorStoreError(StorageError)`**: Raised on database query execution failure or connection failure.
- **`DocumentNotFoundError(VectorStoreError)`**: Raised when an operation targets a non-existent document.
- **`ConnectionPoolError(VectorStoreError)`**: Raised when connection pool lifecycle or acquisition fails.

### 3.3 Vector Store Client: `src/storage/vector_store.py`
Implement `VectorStoreClient` providing asynchronous persistence and vector search on pgvector:

- **Initialization & Lifecycle**:
  - `__init__(connection_string: str | None = None, min_size: int = 1, max_size: int = 10, pool: AsyncConnectionPool | None = None)`:
    Accepts an optional pre-configured `AsyncConnectionPool` for dependency injection and mocking in unit tests.
  - `async def open() -> None`: Initializes the internal connection pool if not already active.
  - `async def close() -> None`: Closes the connection pool and all open connections.
  - Async context manager protocol (`__aenter__` and `__aexit__`) for automated resource cleanup.

- **Methods**:
  - `async def upsert_document(self, metadata: FilingMetadata) -> UUID`:
    - Inserts a document into `documents`.
    - Handles conflict on `accession_number` (`ON CONFLICT (accession_number) DO UPDATE ...`).
    - Returns the UUID of the inserted/updated document.
  - `async def upsert_chunks(self, document_id: UUID, chunks: Sequence[DocumentChunk]) -> list[UUID]`:
    - Batches chunk insertion into `chunks`.
    - Handles conflict on `(document_id, chunk_index)`.
    - Returns list of `chunk_id` UUIDs corresponding to the chunks in index order.
  - `async def upsert_embeddings(self, chunk_ids: Sequence[UUID], embeddings: Sequence[list[float]], model_name: str = "text-embedding-3-small") -> None`:
    - Inserts dense vector embeddings into `embeddings`.
    - Handles conflict on `chunk_id` (`ON CONFLICT (chunk_id) DO UPDATE ...`).
    - Formats vector values for pgvector storage.
  - `async def similarity_search(self, query_vector: list[float], top_k: int = 5, filters: dict[str, Any] | None = None) -> list[SearchResult]`:
    - Performs nearest-neighbor search joining `embeddings`, `chunks`, and `documents`.
    - Uses HNSW index with cosine distance operator (`e.embedding <=> %s::vector`).
    - Supports dynamic filters (`ticker`, `cik`, `section_name`, `form_type`, `period`).
    - Returns top `k` results ordered by similarity ascending distance / descending similarity.
  - `async def delete_document(self, document_id: UUID) -> bool`:
    - Deletes document by `id`.
    - Relies on PostgreSQL `ON DELETE CASCADE` to delete child chunks and embeddings.
    - Returns `True` if a record was deleted, `False` if not found.

### 3.4 Package Exports: `src/storage/__init__.py`
Exports `VectorStoreClient`, `SearchResult`, `StorageError`, `VectorStoreError`, `DocumentNotFoundError`, and `ConnectionPoolError` alongside existing migration functions.

---

## 4. Testing (`tests/unit/storage/` and `tests/integration/storage/`)

### 4.1 Unit Testing (Mocked Pool)
All unit tests mock the `AsyncConnectionPool` and cursor protocols without requiring an active PostgreSQL service.

#### File structure:
```
tests/unit/storage/
├── test_schema.py                # Existing migration & schema tests
└── test_vector_store.py          # Unit tests for VectorStoreClient
```

#### `test_vector_store.py`
| Test | Verifies |
|---|---|
| `test_client_open_and_close` | Initializes pool and closes cleanly on teardown |
| `test_client_async_context_manager` | Enters and exits async context manager properly |
| `test_upsert_document_success` | Executes document upsert query and returns UUID |
| `test_upsert_document_db_error` | Wraps database execution error in `VectorStoreError` |
| `test_upsert_chunks_empty` | Returns empty list when given no chunks |
| `test_upsert_chunks_success` | Inserts chunks batch and returns generated chunk IDs |
| `test_upsert_embeddings_success` | Inserts embeddings batch with model name |
| `test_upsert_embeddings_length_mismatch` | Raises `ValueError` when chunk_ids and embeddings lengths differ |
| `test_similarity_search_no_filter` | Executes vector distance query with LIMIT and maps to `SearchResult` |
| `test_similarity_search_with_filters` | Adds WHERE clauses for ticker, section_name, and period correctly |
| `test_similarity_search_empty_results` | Returns empty list when no vectors match |
| `test_delete_document_success` | Executes delete and returns `True` when document deleted |
| `test_delete_document_not_found` | Returns `False` when no row was deleted |

### 4.2 Integration Testing (Live pgvector)
Tests executed against real PostgreSQL + pgvector Docker container (`make up`).

#### File structure:
```
tests/integration/
└── storage/
    └── test_vector_store_integration.py
```

| Test | Verifies |
|---|---|
| `test_full_crud_lifecycle_live_pgvector` | Ingests document, chunks, embeddings, searches by vector, deletes document |
| `test_cascade_delete_live_pgvector` | Verifies deleting document deletes related chunks and embeddings |
| `test_similarity_search_top_k_ordering` | Verifies closest vector yields highest similarity score |

### Execution commands:

```bash
# Run unit tests with coverage
pytest tests/unit/storage/ -v --cov=src/storage --cov-report=term-missing --cov-fail-under=90

# Run all unit tests
pytest tests/unit/

# Run integration tests (requires docker container up)
pytest tests/integration/storage/ -v
```

---

## 5. Code Quality

```bash
make format      # Auto-format with ruff
make lint        # ruff linter
make type-check  # strict mypy
make check       # lint + type-check combined
```

---

## 6. Push to GitHub and Close

```bash
# Commit changes
git add pyproject.toml src/storage/ tests/unit/storage/ tests/integration/ docs/issue_9_vector_store_client.md
git commit -m "feat(storage): build vector store client with pgvector (#9)"

# Push branch
git push -u origin feature/issue-9-vector-store-client

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(storage): build vector store client with pgvector (#9)" \
  --body "Closes #9.
- Added \`psycopg[binary,pool]>=3.1.18\` dependency for connection pooling.
- Implemented \`VectorStoreClient\` with async \`AsyncConnectionPool\`.
- Implemented \`upsert_document()\`, \`upsert_chunks()\`, and \`upsert_embeddings()\`.
- Implemented \`similarity_search()\` with cosine distance (\`<=>\`) and dynamic metadata filtering.
- Implemented \`delete_document()\` with cascade verification.
- Added unit tests with mocked connection pool (coverage >= 90%).
- Added integration tests against Docker pgvector container."
```

---

## Closing Criteria

- [ ] `pytest tests/unit/storage/ --cov-fail-under=90` passes with no errors.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #9`.
