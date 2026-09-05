# Workflow and Specification: Issue 1 — SEC EDGAR API Client with Rate Limiting

**Milestone**: M1: SEC EDGAR Ingestion & Document Parsing  
**GitHub Issue**: #1  
**Branch**: `feature/issue-1-edgar-client`

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-1-edgar-client
```

---

## 2. Configure Dependencies

### 2.1 Modify `pyproject.toml`
Manually edit [`pyproject.toml`](../pyproject.toml) and replace line 15:

```diff
-dependencies = []
+dependencies = [
+    "httpx>=0.27.0",
+]
```

> [!NOTE]
> While you're there, also remove the obsolete ruff ignore rules on line 36:
> ```diff
> -ignore = ["ANN101", "ANN102"]
> +ignore = []
> ```

### 2.2 Install into the virtual environment

```bash
# Activate the virtual environment
source .venv/bin/activate

# Install updated dependencies
pip install -e ".[dev]"

# Verify
python -c "import httpx; print('httpx OK:', httpx.__version__)"
```

---

## 3. Development (files to create in `src/ingestion/`)

### 3.1 `exceptions.py`
Domain exceptions:
- `EdgarClientError(Exception)` — base.
- `InvalidUserAgentError(EdgarClientError)` — empty, missing email, or placeholder (`"Your Name your@email.com"`) User-Agent.
- `EdgarRateLimitError(EdgarClientError)` — retries exhausted on HTTP 429.
- `EdgarAPIError(EdgarClientError)` — non-recoverable HTTP errors (4xx non-429, persistent 5xx). Stores `status_code`.
- `EdgarRequestError(EdgarClientError)` — transport or timeout error after retries are exhausted.

### 3.2 `rate_limiter.py` — `AsyncTokenBucket`
Async token bucket algorithm enforcing the SEC's 10 req/s limit:
- **Capacity:** 10 tokens. **Rate:** 10.0 tokens/second.
- **Concurrency safety:** `asyncio.Lock`.
- **`async def acquire(tokens: int = 1)`:** Calculates available tokens using `time.monotonic()`. If insufficient, calls `await asyncio.sleep(wait_time)`.

### 3.3 `edgar_client.py` — `EdgarClient`
Async HTTP client built on `httpx.AsyncClient`:
- **Parameters:** `user_agent`, `base_url="https://data.sec.gov"`, `rate_limit_per_sec=10.0`, `max_retries=3`, `backoff_factor=1.0`, `timeout=30.0`, `transport=None` (for injecting `MockTransport` in tests).
- **User-Agent validation:** Regex requiring a valid email, rejecting the default placeholder.
- **Retry logic (max 3 retries, 4 total attempts):**
  - Retries on: `429`, `500`, `502`, `503`, `504`, `httpx.TransportError`, `httpx.TimeoutException`.
  - If the 429 response includes a `Retry-After` header, sleep that exact value.
  - Otherwise apply: `delay = backoff_factor * (2 ** attempt) + random.uniform(0, 0.5)`.
  - `400`, `401`, `403`, `404` fail immediately without retrying.
- **Public methods:**
  - `async def get(url, params, headers) -> httpx.Response`
  - `async def get_json(url, params) -> dict[str, Any]`
  - `async def get_text(url, params) -> str`
  - `async def get_company_submissions(cik: str | int) -> dict[str, Any]` — zero-pads CIK to 10 digits: `/submissions/CIK0000320193.json`.
- **Context manager:** `async with EdgarClient(...) as client:`.

### 3.4 `__init__.py`
Export `EdgarClient`, `AsyncTokenBucket`, and all exceptions.

---

## 4. Testing (`tests/unit/ingestion/`)

All tests use `httpx.MockTransport` — no real SEC network calls.

### File structure to create:
```
tests/unit/ingestion/
├── __init__.py
├── test_rate_limiter.py
└── test_edgar_client.py
```

### `test_rate_limiter.py`
| Test | Verifies |
|---|---|
| `test_initial_burst` | First 10 tokens acquired without delay |
| `test_throttling` | 11th token sleeps ~100ms |
| `test_refill_over_time` | After sleeping 0.5s, 5 tokens are replenished |
| `test_concurrency` | `asyncio.gather` with 15 tasks respects the rate |

### `test_edgar_client.py`
| Test | Verifies |
|---|---|
| `test_user_agent_empty` | Raises `InvalidUserAgentError` |
| `test_user_agent_placeholder` | Rejects `"Your Name your@email.com"` |
| `test_user_agent_no_email` | Raises `InvalidUserAgentError` |
| `test_user_agent_valid` | Initializes without error |
| `test_headers_sent` | `User-Agent` header is present in every request |
| `test_get_json_200` | Returns parsed dict |
| `test_get_text_200` | Returns decoded string |
| `test_get_company_submissions_cik_format` | CIK `320193` → `CIK0000320193.json` |
| `test_retry_429_eventual_success` | 2× 429 → success on 3rd attempt |
| `test_retry_429_exhausted` | 4× 429 → `EdgarRateLimitError` |
| `test_retry_after_respected` | Sleeps the value from `Retry-After` header |
| `test_retry_503_eventual_success` | Transient 503 → success |
| `test_500_exhausted` | 4× 500 → `EdgarAPIError(status_code=500)` |
| `test_404_no_retry` | Fails immediately without retrying |
| `test_403_no_retry` | Fails immediately without retrying |
| `test_timeout_exhausted` | `ConnectTimeout` → `EdgarRequestError` |
| `test_context_manager` | Opens and closes session cleanly with `async with` |

### Execution commands:

```bash
# All ingestion tests with coverage (target: ≥ 90%)
pytest tests/unit/ingestion/ -v --cov=src/ingestion --cov-report=term-missing --cov-fail-under=90

# Rate limiter only
pytest tests/unit/ingestion/test_rate_limiter.py -v

# EDGAR client only
pytest tests/unit/ingestion/test_edgar_client.py -v

# Single test
pytest tests/unit/ingestion/test_edgar_client.py::test_retry_429_exhausted -v
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
# Commit (one commit per logical block or a single final commit)
git add pyproject.toml src/ingestion/ tests/unit/ingestion/
git commit -m "feat(ingestion): implement SEC EDGAR API client with rate limiting (#1)"

# Push branch
git push -u origin feature/issue-1-edgar-client

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(ingestion): SEC EDGAR API client with rate limiting (#1)" \
  --body "Closes #1.
- httpx dependency added.
- AsyncTokenBucket rate limiter (10 req/s).
- EdgarClient with User-Agent validation and exponential backoff.
- 100% mocked unit tests, coverage ≥ 90%."
```

---

## Closing Criteria

- [ ] `pytest tests/unit/ingestion/ --cov-fail-under=90` passes with no errors.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #1`.
