# Workflow and Specification: Issue 7 — Implement Section-Aware Chunker for 10-K Documents

**Milestone**: M2: Semantic Chunking, Embeddings & pgvector Storage  
**GitHub Issue**: #7  
**Branch**: `feature/issue-7-section-aware-chunker`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-7-section-aware-chunker
```

---

## 2. Configure Dependencies

### 2.1 Dependencies in `pyproject.toml`

Add `langchain-text-splitters` and `tiktoken` to `dependencies` in [`pyproject.toml`](../pyproject.toml):

```diff
 dependencies = [
     "httpx>=0.27.0",
     "beautifulsoup4>=4.12.0",
     "lxml>=5.2.0",
     "pydantic>=2.7.0",
     "psycopg[binary]>=3.1.18",
     "pgvector>=0.3.0",
+    "langchain-text-splitters>=0.3.0",
+    "tiktoken>=0.7.0",
 ]
```

### 2.2 Install into the virtual environment

Activate your `.venv` and install the new dependencies:

```bash
# Activate virtual environment
source .venv/bin/activate

# Install updated dependencies in editable mode
pip install -e ".[dev]"
```

### 2.3 Verification

```bash
# Verify langchain-text-splitters and tiktoken are installed
python -c "import langchain_text_splitters; import tiktoken; print('chunking dependencies OK')"
```

---

## 3. Development (files in `src/indexing/`)

### 3.1 Data Model: `src/indexing/models.py`
Define the chunk representation data model using Pydantic:

- **`DocumentChunk(BaseModel)`**:
  - `content: str`: Plain text content of the chunk.
  - `section_name: str`: Canonical section name (e.g. `'item_1'`, `'item_1a'`).
  - `document_id: str | None = None`: Optional document UUID or accession number.
  - `chunk_index: int`: Zero-based sequential position within the document.
  - `token_count: int`: Exact token count of `content` (must be non-negative).
  - Validation:
    - Validates `content` is not empty.
    - Validates `chunk_index >= 0` and `token_count >= 0`.

### 3.2 Chunker Service: `src/indexing/chunker.py`
Implement `SectionAwareChunker` wrapping LangChain's `RecursiveCharacterTextSplitter`:

- **Initialization (`__init__`)**:
  - `chunk_size: int = 512`: Maximum token count per chunk.
  - `chunk_overlap: int = 50`: Token overlap between consecutive chunks.
  - `encoding_name: str = "cl100k_base"`: Tiktoken tokenizer encoding (OpenAI standard).
  - Configures `RecursiveCharacterTextSplitter` with token-based length function and hierarchical separators (`["\n\n", "\n", ". ", " ", ""]`).

- **Methods**:
  - `count_tokens(self, text: str) -> int`: Returns exact token count using tiktoken encoding.
  - `chunk_section(self, section_name: str, text: str, document_id: str | None = None, start_index: int = 0) -> list[DocumentChunk]`:
    - Discards empty or whitespace-only sections.
    - Splits text into secondary chunks when token count exceeds `chunk_size`.
    - Annotates each chunk with `section_name`, `document_id`, sequential `chunk_index`, and `token_count`.
  - `chunk_document(self, document: ParsedDocument, document_id: str | None = None) -> list[DocumentChunk]`:
    - Primary split: Iterates through `document.sections` preserving SEC Item boundaries.
    - Chunks from different sections are **never merged** into the same chunk.
    - Maintains a global sequential `chunk_index` across the entire document.

### 3.3 Package Exports: `src/indexing/__init__.py`
Exports `DocumentChunk` and `SectionAwareChunker`.

---

## 4. Testing (`tests/unit/indexing/`)

Unit tests verifying boundary preservation, token limits, overlap, metadata, and indexing.

### File structure to create:
```
tests/unit/indexing/
├── __init__.py
└── test_chunker.py               # Unit tests for section-aware chunker
```

### `test_chunker.py`
| Test | Verifies |
|---|---|
| `test_document_chunk_model_valid` | Creates `DocumentChunk` with valid fields and asserts properties |
| `test_document_chunk_model_invalid_token_count` | Rejects negative `token_count` or negative `chunk_index` |
| `test_count_tokens_accuracy` | Verifies `count_tokens` accurately counts tokens using `tiktoken` |
| `test_chunk_single_section_under_limit` | Keeps short section as a single chunk without unnecessary splitting |
| `test_chunk_single_section_over_limit` | Splits long section into multiple chunks each under `chunk_size` |
| `test_chunk_overlap_preservation` | Verifies consecutive chunks share overlap text across split boundaries |
| `test_chunk_preserves_section_boundary` | Verifies chunks never cross section boundaries (Item 1 never merges with Item 1A) |
| `test_chunk_document_sequential_indexing` | Verifies `chunk_index` increments monotonically across sections |
| `test_chunk_document_metadata_propagation` | Verifies `section_name` and `document_id` are attached to all chunks |
| `test_chunk_empty_section_ignored` | Empty or whitespace-only sections produce zero chunks |
| `test_chunk_custom_size_and_overlap` | Respects user-defined `chunk_size` and `chunk_overlap` parameters |

### Execution commands:

```bash
# Run all unit tests with coverage
pytest tests/unit/indexing/ -v --cov=src/indexing --cov-report=term-missing --cov-fail-under=90

# Run chunker tests only
pytest tests/unit/indexing/test_chunker.py -v
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
git add pyproject.toml src/indexing/ tests/unit/indexing/ docs/issue_7_section_aware_chunker.md
git commit -m "feat(indexing): implement section-aware chunker for 10-K documents (#7)"

# Push branch
git push -u origin feature/issue-7-section-aware-chunker

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(indexing): implement section-aware chunker for 10-K documents (#7)" \
  --body "Closes #7.
- Added \`langchain-text-splitters>=0.3.0\` and \`tiktoken>=0.7.0\` dependencies.
- Created \`DocumentChunk\` data model with token count and section metadata.
- Implemented \`SectionAwareChunker\` preserving SEC 10-K Item section boundaries.
- Configured secondary splitting with 512 max tokens and 50-token overlap.
- Added comprehensive unit tests for boundary preservation, indexing, and overlap (coverage >= 90%)."
```

---

## Closing Criteria

- [ ] `pytest tests/unit/indexing/ --cov-fail-under=90` passes with no errors.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #7`.
