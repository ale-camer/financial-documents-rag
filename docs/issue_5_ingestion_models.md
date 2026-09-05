# Workflow and Specification: Issue 5 — Ingestion Data Models and Validation

**Milestone**: M1: SEC EDGAR Ingestion & Document Parsing  
**GitHub Issue**: #5  
**Branch**: `feature/issue-5-ingestion-models`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-5-ingestion-models
```

---

## 2. Configure Dependencies

### 2.1 Dependencies in `pyproject.toml`

Add `pydantic` (v2) to `dependencies` in [`pyproject.toml`](../pyproject.toml):

```diff
 dependencies = [
     "httpx>=0.27.0",
     "beautifulsoup4>=4.12.0",
     "lxml>=5.2.0",
+    "pydantic>=2.7.0",
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
# Verify pydantic v2 is installed
python -c "import pydantic; print('pydantic OK:', pydantic.__version__)"
```

---

## 3. Development (files in `src/ingestion/`)

### 3.1 `models.py`
Define Pydantic v2 models representing ingestion data structures:

- **`FilingMetadata(BaseModel)`:**
  - Fields:
    - `cik: str`: SEC Central Index Key (10-digit zero-padded string).
    - `ticker: str | None = None`: Optional trading ticker symbol (auto-capitalized).
    - `period: str`: Fiscal period end date (e.g. `'2023-09-30'`).
    - `accession_number: str`: SEC filing accession number (e.g. `'0000320193-23-000106'`).
    - `form_type: str = "10-K"`: SEC form designation (e.g. `'10-K'`).
  - Validation:
    - `@field_validator("cik", mode="before")`: Accepts `str` or `int`, strips whitespace, validates that it consists only of digits with at most 10 digits, and zero-pads to 10 characters (`zfill(10)`). Rejects non-numeric, negative, or empty values.
    - `@field_validator("accession_number")`: Validates standard SEC accession format `^\d{10}-\d{2}-\d{6}$`.
    - `@field_validator("form_type")`: Normalizes to uppercase and ensures non-empty string.

- **`ParsedSection(BaseModel)`:**
  - Fields:
    - `section_name: str`: Canonical section name (e.g. `'item_1'`, `'item_1a'`).
    - `raw_text: str`: Extracted plain text content of the section.
    - `word_count: int`: Number of words in the section.
  - Validation:
    - `@model_validator(mode="before")`: If `word_count` is not provided or `None`, automatically calculates word count as `len(raw_text.split())`.
    - Validates that `word_count >= 0`.

- **`ParsedDocument(BaseModel)`:**
  - Fields:
    - `metadata: FilingMetadata`: Document filing metadata.
    - `sections: list[ParsedSection]`: List of extracted document sections.
  - Helper Methods & Properties:
    - `get_section(self, section_name: str) -> ParsedSection | None`: Retrieves a section by its canonical name.
    - `@property total_word_count(self) -> int`: Sums the word counts across all sections.

### 3.2 `__init__.py`
Export `FilingMetadata`, `ParsedSection`, and `ParsedDocument`.

---

## 4. Testing (`tests/unit/ingestion/`)

Unit tests verifying model instantiation, field validation, normalization, and edge cases.

### File structure to create:
```
tests/unit/ingestion/
└── test_models.py                # Unit tests for Pydantic v2 ingestion models
```

### `test_models.py`
| Test | Verifies |
|---|---|
| `test_filing_metadata_valid` | Creates metadata with valid fields and normalized CIK |
| `test_filing_metadata_cik_padding_int` | Zero-pads integer CIK `320193` to `'0000320193'` |
| `test_filing_metadata_cik_padding_str` | Zero-pads unpadded string CIK `'320193'` to `'0000320193'` |
| `test_filing_metadata_cik_invalid_non_numeric` | Raises `ValidationError` when CIK contains non-digits |
| `test_filing_metadata_cik_too_long` | Raises `ValidationError` when CIK exceeds 10 digits |
| `test_filing_metadata_accession_number_invalid` | Raises `ValidationError` for malformed accession numbers |
| `test_filing_metadata_ticker_capitalization` | Automatically converts lowercase ticker `'aapl'` to `'AAPL'` |
| `test_parsed_section_auto_word_count` | Automatically computes `word_count` from `raw_text` when omitted |
| `test_parsed_section_explicit_word_count` | Preserves explicitly provided word count |
| `test_parsed_document_get_section_found` | Retrieves existing section by name |
| `test_parsed_document_get_section_missing` | Returns `None` when requested section does not exist |
| `test_parsed_document_total_word_count` | Correctly computes total word count across all document sections |

### Execution commands:

```bash
# Run all unit tests with coverage
pytest tests/unit/ingestion/ -v --cov=src/ingestion --cov-report=term-missing --cov-fail-under=90

# Run model tests only
pytest tests/unit/ingestion/test_models.py -v

# Run a specific test
pytest tests/unit/ingestion/test_models.py::test_filing_metadata_cik_padding_int -v
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
git add pyproject.toml src/ingestion/ tests/unit/ingestion/ docs/issue_5_ingestion_models.md
git commit -m "feat(ingestion): add ingestion data models and validation (#5)"

# Push branch
git push -u origin feature/issue-5-ingestion-models

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(ingestion): add ingestion data models and validation (#5)" \
  --body "Closes #5.
- Added \`pydantic>=2.7.0\` dependency.
- Defined \`FilingMetadata\`, \`ParsedSection\`, and \`ParsedDocument\` models.
- Implemented CIK 10-digit zero-padding and accession number validation.
- Added unit tests for validation rules and edge cases (coverage >= 90%)."
```

---

## 7. Milestone M1 Release: Merge `develop` into `main`

Since Issue 5 completes **Milestone M1 (SEC EDGAR Ingestion & Document Parsing)**, once the PR for Issue 5 is reviewed and merged into `develop`, merge `develop` into `main` and create a release tag:

```bash
# Switch to main branch and fetch latest
git checkout main
git pull origin main

# Merge develop into main without fast-forward
git merge --no-ff develop -m "release: Milestone M1 — SEC EDGAR Ingestion & Document Parsing"

# Tag the milestone release
git tag -a v0.1.0 -m "Milestone M1: SEC EDGAR Ingestion & Document Parsing complete"

# Push main and tag to remote
git push origin main --tags

# Return to develop for upcoming milestone
git checkout develop
```

---

## Closing Criteria

- [ ] `pytest tests/unit/ingestion/ --cov-fail-under=90` passes with no errors.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #5`.
- [ ] PR #5 merged into `develop`.
- [ ] `develop` merged into `main` and tagged `v0.1.0` (Milestone M1 release).

