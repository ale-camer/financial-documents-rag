# Workflow and Specification: Issue 2 — Build 10-K Filing Downloader

**Milestone**: M1: SEC EDGAR Ingestion & Document Parsing  
**GitHub Issue**: #2  
**Branch**: `feature/issue-2-filing-downloader`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-2-filing-downloader
```

---

## 2. Configure Dependencies

### 2.1 Dependencies in `pyproject.toml`

> [!IMPORTANT]
> `pathlib` is a **built-in module** in Python's Standard Library (included by default in Python >= 3.4, and this project requires Python >= 3.11).
> 
> **Do not** add `pathlib` to `dependencies` in `pyproject.toml`. (The PyPI package named `pathlib` is an obsolete, unmaintained backport for Python 2 that should never be installed in Python 3.11+).
>
> `pyproject.toml` dependencies remain unchanged:
```toml
# Runtime dependencies (to be filled per issue)
dependencies = [
    "httpx>=0.27.0"
]
```

### 2.2 Install into the virtual environment

Activate your `.venv` and ensure the editable package is installed:

```bash
# Activate virtual environment
source .venv/bin/activate

# Install / update dependencies in editable mode
pip install -e ".[dev]"
```

### 2.3 Verification

```bash
# Verify both pathlib (built-in) and httpx are ready
python -c "import pathlib, httpx; print('pathlib (stdlib) and httpx OK')"
```

---

## 3. Development (files in `src/ingestion/`)

### 3.1 `exceptions.py`
Add downloader-specific exceptions:
- `FilingNotFoundError(EdgarClientError)` — raised when no 10-K filings are found for the requested CIK or criteria.
- `FilingDownloadError(EdgarClientError)` — raised when an error occurs during filing document download or local file saving.

### 3.2 `filing_downloader.py` — `FilingDownloader`
High-level service class to locate, filter, and download 10-K filings locally:
- **Constructor:**
  - `client: EdgarClient | None = None` (uses provided client or instantiates one from environment variable `SEC_EDGAR_USER_AGENT`).
  - `storage_dir: Path | str = "data/raw"` (configurable root directory where filings are saved).
- **Core Methods:**
  - `async def get_10k_filings(self, cik: str | int, limit: int = 1) -> list[dict[str, Any]]`:
    - Calls `client.get_company_submissions(cik)`.
    - Parses the columnar `filings["recent"]` payload into individual filing dictionaries.
    - Filters filings strictly matching `form == "10-K"`.
    - Returns the top `limit` most recent filings, with extracted fields: `accessionNumber`, `filingDate`, `reportDate`, `form`, `primaryDocument`.
  - `async def download_filing_document(self, cik: str | int, accession_number: str, primary_document: str) -> Path`:
    - Resolves SEC EDGAR archive path:
      - `cik_int = str(int(str(cik).strip()))` (CIK stripped of leading zeros).
      - `accession_clean = accession_number.replace("-", "")`.
      - URL path: `f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_clean}/{primary_document}"`.
    - Downloads primary document HTML/text content using `client.get_text()`.
    - Writes content to `self.storage_dir / str(cik).zfill(10) / accession_number / primary_document`.
    - Ensures parent directories are created automatically (`parents=True, exist_ok=True`).
    - Returns the local destination `Path`.
  - `async def download_recent_10k(self, cik: str | int, limit: int = 1) -> list[Path]`:
    - Orchestrator: calls `get_10k_filings()`, then iterates and calls `download_filing_document()` for each filing.
    - Returns list of local file paths for all downloaded 10-K documents.

### 3.3 `__init__.py`
Export `FilingDownloader`, `FilingNotFoundError`, and `FilingDownloadError`.

---

## 4. Testing (`tests/unit/ingestion/`)

All tests use `httpx.MockTransport` and `tmp_path` (pytest temporary directory fixture) to ensure tests never touch real network or pollute local disk.

### File structure to create/update:
```
tests/unit/ingestion/
├── fixtures/
│   └── submissions_sample.json   # Mock SEC submissions JSON response
└── test_filing_downloader.py     # Downloader unit tests
```

### `test_filing_downloader.py`
| Test | Verifies |
|---|---|
| `test_get_10k_filings_filters_forms` | Extracts only forms with `form == '10-K'`, ignoring 10-Q, 8-K |
| `test_get_10k_filings_respects_limit` | Returns exactly `limit` entries when multiple 10-Ks exist |
| `test_get_10k_filings_no_results` | Returns empty list when no 10-K filings exist in submissions |
| `test_get_10k_filings_missing_recent_field` | Gracefully handles malformed JSON without `recent` key |
| `test_download_filing_document_success` | Downloads HTML document and saves to expected local file path |
| `test_download_filing_document_creates_directories` | Creates target directory hierarchy if it doesn't exist |
| `test_download_filing_document_error` | Raises `FilingDownloadError` when client fails or returns error |
| `test_download_recent_10k_orchestration` | Coordinates metadata fetch + download, returning list of saved Paths |
| `test_custom_storage_dir` | Honors custom `storage_dir` path passed to constructor |

### Execution commands:

```bash
# Run all unit tests with coverage
pytest tests/unit/ingestion/ -v --cov=src/ingestion --cov-report=term-missing --cov-fail-under=90

# Run filing downloader tests only
pytest tests/unit/ingestion/test_filing_downloader.py -v

# Run a specific test
pytest tests/unit/ingestion/test_filing_downloader.py::test_download_recent_10k_orchestration -v
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
git add src/ingestion/ tests/unit/ingestion/ docs/issue_2_filing_downloader.md
git commit -m "feat(ingestion): build 10-K filing downloader (#2)"

# Push branch
git push -u origin feature/issue-2-filing-downloader

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(ingestion): build 10-K filing downloader (#2)" \
  --body "Closes #2.
- Implemented \`FilingDownloader\` to fetch and filter 10-K submissions.
- Added document download and local storage management with directory creation.
- Added unit tests with mocked transports and fixtures (coverage >= 90%)."
```

---

## Closing Criteria

- [ ] `pytest tests/unit/ingestion/ --cov-fail-under=90` passes with no errors.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #2`.
