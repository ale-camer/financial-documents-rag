# Workflow and Specification: Issue 14 — FastAPI Service and Endpoints

**Milestone**: M4: FastAPI Service, Citation Layer & Evaluation  
**GitHub Issue**: #14  
**Branch**: `feature/issue-14-fastapi-service`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-14-fastapi-service
```

---

## 2. Development

### 2.1 API Schemas (`src/api/schemas.py`)
Define Pydantic models for the requests and responses.

- **QueryRequest**:
  - `query` (str): The user's question.
  - `filters` (dict, optional): Metadata filters (e.g., ticker).

- **QueryResponse**:
  - `answer` (str): The generated answer.
  - `source_documents` (list[dict]): The chunks used to generate the answer.

- **IngestRequest**:
  - `ticker` (str): Company ticker.
  - `form_type` (str): Defaults to "10-K".

### 2.2 FastAPI Application (`src/api/main.py`)
Set up the FastAPI app with the required endpoints.

- **Dependencies**:
  - Inject the `RAGPipeline` (for querying).

- **Endpoints**:
  - `GET /health`: Returns `{"status": "ok"}`.
  - `POST /query`: Accepts `QueryRequest`, calls `RAGPipeline.ask()`, returns `QueryResponse`.
  - `POST /ingest`: Accepts `IngestRequest`, triggers the ingestion and indexing pipeline.

### 2.3 Dependencies Setup (`src/api/dependencies.py`)
- Define functions to initialize and provide the Singletons for `HybridRetriever`, `RAGGenerator`, and `RAGPipeline` using FastAPI's `Depends`.

---

## 3. Testing (`tests/unit/api/test_endpoints.py`)

### 3.1 Unit Testing

| Test | Verifies |
|---|---|
| `test_health_check` | Verifies `/health` returns 200 OK. |
| `test_query_endpoint_success` | Verifies `/query` correctly calls the pipeline and returns 200 with the answer. |
| `test_query_endpoint_missing_query` | Verifies validation error when query is missing. |

### Execution commands:

```bash
# Run unit tests
pytest tests/unit/api/ -v
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
git add src/api/ tests/unit/api/ docs/issue_14_fastapi_service.md
git commit -m "feat(api): implement fastapi service endpoints (#14)"

# Push branch
git push -u origin feature/issue-14-fastapi-service

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(api): implement fastapi service endpoints (#14)" \
  --body "Closes #14.
- Created FastAPI app with \`/health\`, \`/query\`, and \`/ingest\` endpoints.
- Defined Pydantic schemas for request/response validation.
- Wired up RAGPipeline using FastAPI dependencies.
- Added unit tests for endpoints."
```

---

## Closing Criteria

- [ ] FastAPI app is configured and runs successfully.
- [ ] Pydantic schemas validate requests correctly.
- [ ] `/health`, `/query`, and `/ingest` endpoints are implemented.
- [ ] Dependencies injection works for `RAGPipeline`.
- [ ] Unit tests pass for API endpoints.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #14`.
