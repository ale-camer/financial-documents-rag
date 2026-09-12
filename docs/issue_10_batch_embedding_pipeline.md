# Workflow and Specification: Issue 10 — Add batch embedding pipeline with progress tracking

**Milestone**: M2: Semantic Chunking, Embeddings & pgvector Storage  
**GitHub Issue**: #10  
**Branch**: `feature/issue-10-batch-embedding-pipeline`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-10-batch-embedding-pipeline
```

---

## 2. Configure Dependencies

### 2.1 Dependencies in `pyproject.toml`

Ensure that `tqdm` is installed for progress tracking. Add it to [`pyproject.toml`](../pyproject.toml) if not present:

```diff
 dependencies = [
     "httpx>=0.27.0",
     "beautifulsoup4>=4.12.0",
     "lxml>=5.2.0",
     "pydantic>=2.7.0",
     "psycopg[binary,pool]>=3.1.18",
     "pgvector>=0.3.0",
     "langchain-text-splitters>=0.3.0",
     "tiktoken>=0.7.0",
     "openai>=1.30.0",
+    "tqdm>=4.66.0",
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

---

## 3. Development (files in `src/indexing/`)

### 3.1 Indexing Pipeline: `src/indexing/pipeline.py`
Implement `IndexingPipeline` to orchestrate chunker, embeddings, and vector store operations:

- **Initialization**:
  - `__init__(chunker: SectionAwareChunker, embedding_service: EmbeddingService, vector_store: VectorStoreClient)`

- **Methods**:
  - `async def process_document(self, document: ParsedDocument, batch_size: int = 100, concurrency: int = 5, show_progress: bool = True) -> None`:
    - **Step 1:** Upsert the document metadata via `self.vector_store.upsert_document` to get the `document_id`.
    - **Step 2:** Chunk the document using `self.chunker.chunk_document`.
    - **Step 3:** Upsert the chunks into the vector store via `self.vector_store.upsert_chunks` to obtain their `chunk_ids`.
    - **Step 4:** Batch the `chunks` and `chunk_ids` using the configured `batch_size`.
    - **Step 5:** Use `asyncio.Semaphore(concurrency)` to limit concurrent tasks for embedding and inserting.
    - **Step 6:** For each batch (using `asyncio.gather`), fetch embeddings via `self.embedding_service.embed_chunks` and insert them into the vector store via `self.vector_store.upsert_embeddings`.
    - **Step 7:** Wrap the batch execution in `tqdm.asyncio.tqdm` to display a progress bar if `show_progress` is `True`.

*(Note: Idempotency is largely handled by the `ON CONFLICT DO UPDATE` statements inside `VectorStoreClient`, which will overwrite existing records. However, if a document shrinks and produces fewer chunks, dangling chunks could remain unless they are explicitly purged. Decide during implementation whether to add a `delete_chunks_by_document_id` method to `VectorStoreClient` or rely on the `ON CONFLICT` strategy).*

---

## 4. Testing (`tests/integration/indexing/`)

### 4.1 Integration Testing (End-to-End Pipeline)
Tests executed against real PostgreSQL + pgvector Docker container and a mock or real OpenAI API.

#### File structure:
```
tests/integration/
└── indexing/
    └── test_pipeline_integration.py
```

| Test | Verifies |
|---|---|
| `test_indexing_pipeline_end_to_end` | Runs `process_document` on a sample 10-K document and verifies db state. |
| `test_indexing_pipeline_idempotency` | Re-indexes the same document with modifications to ensure chunks/embeddings are correctly updated/replaced. |

### Execution commands:

```bash
# Run integration tests (requires docker container up)
pytest tests/integration/indexing/test_pipeline_integration.py -v
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
git add pyproject.toml src/indexing/ tests/integration/ docs/issue_10_batch_embedding_pipeline.md
git commit -m "feat(indexing): build batch embedding pipeline with progress tracking (#10)"

# Push branch
git push -u origin feature/issue-10-batch-embedding-pipeline

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(indexing): build batch embedding pipeline with progress tracking (#10)" \
  --body "Closes #10.
- Added \`IndexingPipeline\` orchestrating chunker, embedding service, and vector store.
- Added \`tqdm\` progress bar for batch operations.
- Implemented batching with configurable size and concurrency limit using semaphores.
- Handled idempotency for re-indexing documents.
- Added integration tests for end-to-end pipeline execution."
```

---

## Closing Criteria

- [ ] `IndexingPipeline` correctly calls components.
- [ ] Integration tests pass without errors.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #10`.
