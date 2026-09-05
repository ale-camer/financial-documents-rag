# Workflow and Specification: Issue 3 — Implement HTML/XBRL Parser for 10-K Documents

**Milestone**: M1: SEC EDGAR Ingestion & Document Parsing  
**GitHub Issue**: #3  
**Branch**: `feature/issue-3-html-parser`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-3-html-parser
```

---

## 2. Configure Dependencies

### 2.1 Dependencies in `pyproject.toml`

Add `beautifulsoup4` and `lxml` to `dependencies` in [`pyproject.toml`](../pyproject.toml):

```diff
 dependencies = [
     "httpx>=0.27.0",
+    "beautifulsoup4>=4.12.0",
+    "lxml>=5.2.0",
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
# Verify bs4 and lxml are available
python -c "import bs4, lxml; print('bs4 and lxml OK')"
```

---

## 3. Development (files in `src/ingestion/`)

### 3.1 `exceptions.py`
Add parser-specific exception:
- `ParserError(EdgarClientError)` — raised when document parsing fails due to unreadable content or severe decoding failures.

### 3.2 `html_parser.py` — `TenKParser`
Core parser class to convert raw 10-K HTML and inline XBRL (iXBRL) documents into clean, structured plain text:
- **Constructor:**
  - `__init__(self, parser: str = "lxml") -> None`:
    - Configures the backend parser engine (`"lxml"` by default, with fallback to `"html.parser"`).
- **Core Methods:**
  - `parse(self, raw_html: str | bytes) -> str`:
    - Accepts raw content as either `str` or `bytes` (decodes `bytes` using UTF-8 with fallback to Latin-1).
    - Removes non-content boilerplate tags: `<script>`, `<style>`, `<head>`, `<meta>`, `<link>`, `<noscript>`.
    - Handles inline XBRL (`iXBRL`):
      - Removes metadata containers (`<ix:header>`, `<ix:hidden>`).
      - Unwraps and extracts inner textual content from data tags (`<ix:nonNumeric>`, `<ix:nonFraction>`, `<ix:continuation>`).
    - Strips noisy sections:
      - Tables of contents with repetitive dot leaders or navigation anchors.
      - Exhibit index sections typically appended at the end of 10-K filings.
    - Preserves section headers:
      - Ensures primary SEC Item headings (e.g., `ITEM 1.`, `ITEM 1A.`, `ITEM 7.`, `ITEM 8.`) are placed on distinct lines and clearly distinguishable for downstream section extraction.
    - Normalizes text:
      - Replaces non-breaking spaces (`\xa0`), zero-width spaces, and HTML entities (`&nbsp;`, `&amp;`, etc.).
      - Consolidates excessive whitespace while maintaining paragraph breaks (`\n\n`).
  - `parse_file(self, file_path: Path | str) -> str`:
    - Reads raw file content from disk and delegates to `parse()`.

### 3.3 `__init__.py`
Export `TenKParser` and `ParserError`.

---

## 4. Testing (`tests/unit/ingestion/`)

All tests use local fixtures and isolated test strings — no network calls.

### File structure to create:
```
tests/unit/ingestion/
├── fixtures/
│   ├── sample_10k.html            # Realistic 10-K HTML with standard sections
│   └── sample_10k_ixbrl.htm       # 10-K snippet with inline XBRL tags
└── test_html_parser.py            # Unit tests for TenKParser
```

### `test_html_parser.py`
| Test | Verifies |
|---|---|
| `test_parse_raw_bytes_and_string` | Accepts both `bytes` and `str` producing identical parsed text |
| `test_strip_script_and_style` | Strips `<script>` and `<style>` blocks and their inner contents |
| `test_handle_inline_xbrl_tags` | Strips `<ix:header>`/`<ix:hidden>` but keeps text within `<ix:nonNumeric>` |
| `test_preserve_section_headers` | Keeps `ITEM 1.`, `ITEM 1A.`, `ITEM 7.` on separate lines |
| `test_strip_table_of_contents` | Removes repetitive TOC dot-leaders and TOC index listings |
| `test_strip_exhibit_index` | Removes exhibit index boilerplate tables at document end |
| `test_normalize_whitespace` | Converts non-breaking spaces and collapses blank lines into `\n\n` |
| `test_parse_file_success` | Reads from a local `Path` file and produces expected parsed text |
| `test_empty_input_handling` | Gracefully returns empty string for empty string or empty bytes |
| `test_malformed_html_handling` | Recovers and parses unclosed tags or malformed HTML snippets |

### Execution commands:

```bash
# Run all unit tests with coverage
pytest tests/unit/ingestion/ -v --cov=src/ingestion --cov-report=term-missing --cov-fail-under=90

# Run HTML parser tests only
pytest tests/unit/ingestion/test_html_parser.py -v

# Run a specific test
pytest tests/unit/ingestion/test_html_parser.py::test_handle_inline_xbrl_tags -v
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
git add pyproject.toml src/ingestion/ tests/unit/ingestion/ docs/issue_3_html_parser.md
git commit -m "feat(ingestion): implement HTML/XBRL parser for 10-K documents (#3)"

# Push branch
git push -u origin feature/issue-3-html-parser

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(ingestion): implement HTML/XBRL parser for 10-K documents (#3)" \
  --body "Closes #3.
- Added \`beautifulsoup4\` and \`lxml\` dependencies in pyproject.toml.
- Implemented \`TenKParser\` for cleaning raw HTML and inline XBRL filings.
- Preserved section headers (Items 1, 1A, 7, 8) and stripped boilerplate/TOC.
- Added unit tests with sample fixtures (coverage >= 90%)."
```

---

## Closing Criteria

- [ ] `pytest tests/unit/ingestion/ --cov-fail-under=90` passes with no errors.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #3`.
