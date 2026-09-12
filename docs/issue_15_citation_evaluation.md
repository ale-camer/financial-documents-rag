# Workflow and Specification: Issue 15 — Citation Layer & Evaluation

**Milestone**: M4: FastAPI Service, Citation Layer & Evaluation  
**GitHub Issue**: #15  
**Branch**: `feature/issue-15-citation-evaluation`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-15-citation-evaluation
```

---

## 2. Development

### 2.1 Citation Extraction Utility (`src/rag/citations.py`)
Implement logic to extract citation markers from the generated LLM text and associate them with the original retrieved chunks.

- **`extract_citations(text: str) -> list[str]`**: Uses Regex to find all `[Document <UUID>]` or `[Item X]` markers.
- **`format_answer_with_citations(answer: str, chunks: list[RetrievedChunk])`**: Matches the markers back to the chunks to return a rich citation response.

### 2.2 Updating the API Schemas (`src/api/schemas.py`)
Enhance the query endpoint response to return structured citations.

- **QueryResponse modifications**:
  - Add `citations: list[dict]` where each dict contains metadata about the chunk (e.g., `document_id`, `chunk_id`, `text`, `similarity`).

### 2.3 Wiring in the Pipeline (`src/api/main.py`)
- Call the citation extraction utility within the `/query` endpoint before returning the response.

### 2.4 Basic Evaluation Script (`scripts/evaluate_rag.py`)
Create a foundational evaluation script to test the pipeline natively.
- Use `LangSmith` (already in `pyproject.toml`) to trace calls.
- Process a batch of test questions (e.g., "What are the key risk factors for Apple?").
- Output a basic report or log the latency and retrieved documents.

---

## 3. Testing (`tests/unit/rag/test_citations.py` & API tests)

### 3.1 Unit Testing

| Test | Verifies |
|---|---|
| `test_extract_citations_success` | Verifies UUIDs and Document markers are correctly parsed via Regex. |
| `test_extract_citations_no_citations` | Verifies the function handles text with no markers gracefully. |
| `test_api_query_returns_citations` | Update existing API tests to verify `citations` field is present and structured. |

### Execution commands:

```bash
# Run unit tests
pytest tests/unit/ -v
```

---

## 4. Documentation and Milestone Closure

- Actualizar `README.md`: Marcar **M4: FastAPI Service, Citation Layer & Evaluation** como completado (✅).

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
git add src/ scripts/ tests/ docs/issue_15_citation_evaluation.md README.md
git commit -m "feat(rag): implement citation layer and basic evaluation (#15)"

# Push branch
git push -u origin feature/issue-15-citation-evaluation

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(rag): implement citation layer and basic evaluation (#15)" \
  --body "Closes #15.
- Added citation extraction utilities with Regex.
- Updated FastAPI schema to return structured citations.
- Added RAG evaluation script using LangSmith.
- Completed Milestone 4."
```

---

## Closing Criteria

- [ ] `citations.py` correctly extracts formatting markers from text.
- [ ] API endpoint `/query` returns structured citation payloads.
- [ ] Evaluation script `scripts/evaluate_rag.py` executes successfully.
- [ ] Tests para las utilidades de citación pasan correctamente.
- [ ] `make check` passes with no warnings.
- [ ] Milestone 4 is marked complete in `README.md`.
- [ ] PR opened against `develop` referencing `Closes #15`.
