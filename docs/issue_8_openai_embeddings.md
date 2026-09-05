# Workflow and Specification: Issue 8 — Integrate OpenAI text-embedding-3-small for Chunk Embeddings

**Milestone**: M2: Semantic Chunking, Embeddings & pgvector Storage  
**GitHub Issue**: #8  
**Branch**: `feature/issue-8-openai-embeddings`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-8-openai-embeddings
```

---

## 2. Configure Dependencies

### 2.1 Dependencies in `pyproject.toml`

Add `openai` to `dependencies` in [`pyproject.toml`](../pyproject.toml):

```diff
 dependencies = [
     "httpx>=0.27.0",
     "beautifulsoup4>=4.12.0",
     "lxml>=5.2.0",
     "pydantic>=2.7.0",
     "psycopg[binary]>=3.1.18",
     "pgvector>=0.3.0",
     "langchain-text-splitters>=0.3.0",
     "tiktoken>=0.7.0",
+    "openai>=1.30.0",
 ]
```

### 2.2 Install into the virtual environment

Activate your `.venv` and install the new dependency:

```bash
# Activate virtual environment
source .venv/bin/activate

# Install updated dependencies in editable mode
pip install -e ".[dev]"
```

### 2.3 Verification

```bash
# Verify openai is installed
python -c "import openai; print('openai OK:', openai.__version__)"
```

---

## 3. Development (files in `src/indexing/`)

### 3.1 Custom Exceptions: `src/indexing/exceptions.py`
Define domain exceptions for indexing and embedding operations:

- **`IndexingError(Exception)`**: Base exception for the indexing module.
- **`TokenLimitExceededError(IndexingError)`**: Raised when an input text exceeds the model limit (8191 tokens).
- **`EmbeddingServiceError(IndexingError)`**: Raised on unrecoverable API errors during embedding generation.
- **`RateLimitExceededError(EmbeddingServiceError)`**: Raised when rate limit (429) retries are exhausted.

### 3.2 Embedding Service: `src/indexing/embeddings.py`
Implement `EmbeddingService` for generating vector representations via OpenAI API:

- **Constants & Configuration**:
  - Default model: `text-embedding-3-small` (1536 dimensions).
  - Maximum tokens per input: `8191`.
  - Maximum batch size: `2048` items per API request.
  - Default retry settings: 3 retries with exponential backoff.

- **Initialization (`__init__`)**:
  - Accepts `client: AsyncOpenAI | None = None` (allowing injected mock client in tests).
  - `api_key: str | None = None`: Optional API key if creating client internally.
  - `model: str = "text-embedding-3-small"`.
  - `dimensions: int = 1536`.
  - `max_batch_size: int = 2048`.
  - `max_retries: int = 3`.
  - `initial_delay: float = 0.5`.

- **Methods**:
  - `count_tokens(self, text: str) -> int`: Counts tokens using `tiktoken.get_encoding("cl100k_base")`.
  - `validate_input_tokens(self, text: str) -> None`: Validates token count does not exceed 8191; raises `TokenLimitExceededError`.
  - `async def embed_texts(self, texts: list[str]) -> list[list[float]]`:
    - Validates all input texts against token limits.
    - Slices inputs into batches of `max_batch_size` (<= 2048 items).
    - Dispatches async API requests to `client.embeddings.create(input=batch, model=self.model)`.
    - Implements exponential backoff on 429 (`RateLimitError`) with jitter/backoff.
    - Preserves exact input order in the returned embeddings list.
  - `async def embed_chunks(self, chunks: list[DocumentChunk]) -> list[list[float]]`:
    - Extracts `chunk.content` for each chunk.
    - Delegates to `embed_texts` and returns embeddings in matching order.
  - `async def embed_query(self, query: str) -> list[float]`:
    - Convenience helper to embed a single natural language query for retrieval.

### 3.3 Package Exports: `src/indexing/__init__.py`
Exports `EmbeddingService`, `IndexingError`, `TokenLimitExceededError`, `EmbeddingServiceError`, and `RateLimitExceededError`.

---

## 4. Testing (`tests/unit/indexing/`)

All tests use mocked `AsyncOpenAI` clients (no live API keys or external network calls).

### File structure to create:
```
tests/unit/indexing/
└── test_embeddings.py            # Unit tests for EmbeddingService
```

### `test_embeddings.py`
| Test | Verifies |
|---|---|
| `test_embed_texts_empty_list` | Returns empty list when given no texts without calling API |
| `test_embed_texts_single_batch` | Successfully generates embeddings for single batch with mocked client |
| `test_embed_texts_multiple_batches` | Correctly partitions inputs exceeding `max_batch_size` across multiple API calls |
| `test_embed_texts_exceeds_token_limit` | Raises `TokenLimitExceededError` when an input exceeds 8191 tokens |
| `test_embed_chunks_delegation` | Extracts contents from `DocumentChunk` instances and returns corresponding embeddings |
| `test_embed_query_single_text` | Returns single 1536-dimensional vector for a query string |
| `test_embed_retry_on_429_success` | Retries with exponential backoff on `RateLimitError` (429) and succeeds |
| `test_embed_retry_exhausted_raises` | Raises `RateLimitExceededError` when max retries are exhausted |
| `test_embed_unrecoverable_api_error` | Immediately raises `EmbeddingServiceError` on non-retryable errors (e.g. 401) |
| `test_embedding_service_custom_model` | Configures and calls custom model (e.g. `text-embedding-3-large`) |

### Execution commands:

```bash
# Run all unit tests with coverage
pytest tests/unit/indexing/ -v --cov=src/indexing --cov-report=term-missing --cov-fail-under=90

# Run embedding tests only
pytest tests/unit/indexing/test_embeddings.py -v
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
git add pyproject.toml src/indexing/ tests/unit/indexing/ docs/issue_8_openai_embeddings.md
git commit -m "feat(indexing): integrate OpenAI embeddings for chunks (#8)"

# Push branch
git push -u origin feature/issue-8-openai-embeddings

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(indexing): integrate OpenAI embeddings for chunks (#8)" \
  --body "Closes #8.
- Added \`openai>=1.30.0\` dependency.
- Implemented \`EmbeddingService\` with async \`embed_chunks\` and \`embed_texts\`.
- Added automatic batching for inputs up to 2048 items.
- Added 8191 token validation per input with \`TokenLimitExceededError\`.
- Implemented retry logic with exponential backoff for 429 rate limit errors.
- Added unit tests with mocked OpenAI client (coverage >= 90%)."
```

---

## Closing Criteria

- [ ] `pytest tests/unit/indexing/ --cov-fail-under=90` passes with no errors.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #8`.
