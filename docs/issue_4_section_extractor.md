# Workflow and Specification: Issue 4 — Extract Structured Sections from 10-K

**Milestone**: M1: SEC EDGAR Ingestion & Document Parsing  
**GitHub Issue**: #4  
**Branch**: `feature/issue-4-section-extractor`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-4-section-extractor
```

---

## 2. Configure Dependencies

### 2.1 Dependencies in `pyproject.toml`

> [!IMPORTANT]
> This issue relies on Python's built-in `re` and `typing` modules from the Standard Library. No new third-party dependencies are required.
>
> `pyproject.toml` dependencies remain unchanged:
```toml
# Runtime dependencies (to be filled per issue)
dependencies = [
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.2.0",
]
```

### 2.2 Install into the virtual environment

Ensure your `.venv` is activated and the development environment is synchronized:

```bash
# Activate virtual environment
source .venv/bin/activate

# Verify dependencies in editable mode
pip install -e ".[dev]"
```

### 2.3 Verification

```bash
# Verify environment is intact
python -c "import re, bs4, lxml, httpx; print('Environment OK')"
```

---

## 3. Development (files in `src/ingestion/`)

### 3.1 `exceptions.py`
Add extractor-specific exception:
- `SectionExtractionError(EdgarClientError)` — raised when an unrecoverable extraction error occurs.

### 3.2 `section_extractor.py` — `SectionExtractor`
Service class to detect and extract standard SEC 10-K sections from parsed filing text:
- **Supported Sections:**
  - `item_1`: Business (Item 1)
  - `item_1a`: Risk Factors (Item 1A)
  - `item_7`: Management's Discussion and Analysis of Financial Condition and Results of Operations (Item 7)
  - `item_7a`: Quantitative and Qualitative Disclosures About Market Risk (Item 7A)
  - `item_8`: Financial Statements and Supplementary Data (Item 8)
- **Heading Pattern & Boundary Detection:**
  - Robust regex identifying section starts (e.g. `ITEM\s+1\b`, `ITEM\s+1A\b`, `ITEM\s+7\b`, `ITEM\s+7A\b`, `ITEM\s+8\b`), accommodating varying punctuation (`.`, `:`, `-`, or whitespace) and case-insensitivity.
  - Precise demarcation preventing section bleed (e.g., Item 1 stops at Item 1A or Item 1B; Item 7 stops at Item 7A or Item 8; Item 7A stops at Item 8; Item 8 stops at Item 9 or 9A).
  - Handles false positives by selecting occurrences with meaningful body text rather than casual inline mentions.
- **Core Methods:**
  - `extract_sections(self, text: str) -> dict[str, str]`:
    - Parses full document text and returns a dictionary mapping section keys (`"item_1"`, `"item_1a"`, etc.) to their respective extracted text spans.
    - Gracefully handles missing sections: sections absent in the document are simply omitted from the returned dictionary (never raises an error for missing sections).
    - Cleans leading and trailing whitespace of extracted section text.
  - `extract_section(self, text: str, section_name: str) -> str | None`:
    - Convenience method to extract a single specified section by key (e.g. `"item_1a"`), returning `None` if the section is not found.
- **Supported Section Key Aliases:**
  - Accepts normalized keys: `"item_1"`, `"item_1a"`, `"item_7"`, `"item_7a"`, `"item_8"` (as well as case-insensitive variations like `"1"`, `"1A"`, `"Item 1"`).

### 3.3 `__init__.py`
Export `SectionExtractor` and `SectionExtractionError`.

---

## 4. Testing (`tests/unit/ingestion/`)

All tests use synthetic text fixtures and real parsed 10-K samples — no network access.

### File structure to create:
```
tests/unit/ingestion/
├── fixtures/
│   └── sample_parsed_10k.txt      # Representative parsed text with Items 1, 1A, 7, 7A, 8
└── test_section_extractor.py      # Unit tests for SectionExtractor
```

### `test_section_extractor.py`
| Test | Verifies |
|---|---|
| `test_extract_all_supported_sections` | Extracts all 5 supported sections (`item_1`, `item_1a`, `item_7`, `item_7a`, `item_8`) |
| `test_extract_single_section` | `extract_section()` correctly retrieves a specific target section |
| `test_missing_section_graceful_handling` | Omits missing sections from result dict without raising errors |
| `test_section_boundaries_no_bleed` | Item 1 does not include Item 1A content; Item 7 does not include Item 7A |
| `test_heading_variation_matching` | Matches headings with colons, dashes, periods, and different casing |
| `test_empty_and_whitespace_input` | Returns empty dict when text is empty or only whitespace |
| `test_no_matching_headings_input` | Returns empty dict when text contains no SEC Item headings |
| `test_key_normalization` | Accepts aliases (`"1"`, `"Item 1"`, `"item_1"`) in `extract_section()` |
| `test_extracted_text_is_trimmed` | Extracted section text has no leading/trailing extraneous whitespace |

### Execution commands:

```bash
# Run all unit tests with coverage
pytest tests/unit/ingestion/ -v --cov=src/ingestion --cov-report=term-missing --cov-fail-under=90

# Run section extractor tests only
pytest tests/unit/ingestion/test_section_extractor.py -v

# Run a specific test
pytest tests/unit/ingestion/test_section_extractor.py::test_section_boundaries_no_bleed -v
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
git add src/ingestion/ tests/unit/ingestion/ docs/issue_4_section_extractor.md
git commit -m "feat(ingestion): extract structured sections from 10-K (#4)"

# Push branch
git push -u origin feature/issue-4-section-extractor

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(ingestion): extract structured sections from 10-K (#4)" \
  --body "Closes #4.
- Implemented \`SectionExtractor\` for SEC 10-K Item detection.
- Supported Item 1, Item 1A, Item 7, Item 7A, and Item 8 extraction.
- Handled missing sections gracefully and prevented boundary bleed.
- Added comprehensive unit tests (coverage >= 90%)."
```

---

## Closing Criteria

- [ ] `pytest tests/unit/ingestion/ --cov-fail-under=90` passes with no errors.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #4`.
