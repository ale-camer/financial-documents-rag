# Workflow and Specification: Issue 6 — Design pgvector Schema (Documents, Chunks, Embeddings Tables)

**Milestone**: M2: Semantic Chunking, Embeddings & pgvector Storage  
**GitHub Issue**: #6  
**Branch**: `feature/issue-6-pgvector-schema`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-6-pgvector-schema
```

---

## 2. Configure Dependencies

### 2.1 Dependencies in `pyproject.toml`

Add `psycopg` (with binary wheels) and `pgvector` to `dependencies` in [`pyproject.toml`](../pyproject.toml):

```diff
 dependencies = [
     "httpx>=0.27.0",
     "beautifulsoup4>=4.12.0",
     "lxml>=5.2.0",
     "pydantic>=2.7.0",
+    "psycopg[binary]>=3.1.18",
+    "pgvector>=0.3.0",
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
# Verify psycopg and pgvector are installed
python -c "import psycopg; import pgvector; print('psycopg & pgvector OK')"
```

---

## 3. Development (files in `src/storage/`)

### 3.1 Migration SQL: `src/storage/migrations/001_initial_schema.sql`
Defines PostgreSQL schema with pgvector extension and core tables:

- **Extensions**:
  - `CREATE EXTENSION IF NOT EXISTS vector;`
  - `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";` (or native `gen_random_uuid()`).

- **`documents` Table**:
  - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `cik VARCHAR(10) NOT NULL`
  - `ticker VARCHAR(10)`
  - `period VARCHAR(20) NOT NULL`
  - `form_type VARCHAR(10) NOT NULL DEFAULT '10-K'`
  - `accession_number VARCHAR(25) NOT NULL UNIQUE`
  - `ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
  - Indexes on `cik`, `ticker`, and `accession_number`.

- **`chunks` Table**:
  - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE`
  - `section_name VARCHAR(50) NOT NULL`
  - `content TEXT NOT NULL`
  - `token_count INTEGER NOT NULL CHECK (token_count >= 0)`
  - `chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0)`
  - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
  - Unique constraint: `UNIQUE (document_id, chunk_index)`
  - Indexes on `document_id` and `section_name`.

- **`embeddings` Table**:
  - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE UNIQUE`
  - `embedding vector(1536) NOT NULL`
  - `model_name VARCHAR(50) NOT NULL DEFAULT 'text-embedding-3-small'`
  - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
  - HNSW Index on `embedding`:
    ```sql
    CREATE INDEX idx_embeddings_hnsw ON embeddings 
    USING hnsw (embedding vector_cosine_ops);
    ```
  - Index on `chunk_id`.

### 3.2 Migration Down SQL: `src/storage/migrations/001_initial_schema.down.sql`
Rollback script:
- Drops tables in reverse dependency order: `embeddings`, `chunks`, `documents`.

### 3.3 Migration Runner: `src/storage/migration_runner.py`
Helper module to manage and execute SQL migration files:
- `get_migrations_dir() -> Path`: Returns the path to the migrations directory.
- `apply_migrations(conn: psycopg.Connection) -> list[str]`:
  - Creates a `schema_migrations` tracking table if it does not exist (`version VARCHAR(255) PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT NOW()`).
  - Reads and executes unapplied `.sql` migration files in alphanumeric order within a transaction.
  - Records applied versions in `schema_migrations`.
- `rollback_migration(conn: psycopg.Connection, version: str) -> bool`:
  - Executes corresponding `.down.sql` script and removes the version record from `schema_migrations`.

### 3.4 Package Exports: `src/storage/__init__.py`
Exports `apply_migrations`, `rollback_migration`, and migration helper utilities.

---

## 4. Testing (`tests/unit/storage/`)

All unit tests use mocked connections and file system fixtures without requiring an active external database.

### File structure to create:
```
tests/unit/storage/
├── __init__.py
└── test_schema.py                # Schema SQL and migration runner unit tests
```

### `test_schema.py`
| Test | Verifies |
|---|---|
| `test_migration_sql_files_exist` | Validates both up and down SQL migration files exist in `src/storage/migrations/` |
| `test_documents_table_definition` | Verifies `documents` table has all required columns, PK, and unique accession constraint |
| `test_chunks_table_definition` | Verifies `chunks` table has document_id FK with CASCADE and required check constraints |
| `test_embeddings_table_definition` | Verifies `embeddings` table has vector(1536) column and chunk_id FK |
| `test_hnsw_index_specification` | Verifies HNSW index is created using `vector_cosine_ops` on `embeddings.embedding` |
| `test_migration_runner_applies_unapplied` | Verifies `apply_migrations` executes SQL and logs version into tracking table |
| `test_migration_runner_skips_already_applied` | Verifies `apply_migrations` is idempotent and skips previously applied versions |
| `test_migration_runner_rollback` | Verifies `rollback_migration` executes `.down.sql` and removes migration record |

### Execution commands:

```bash
# Run all unit tests with coverage
pytest tests/unit/storage/ -v --cov=src/storage --cov-report=term-missing --cov-fail-under=90

# Run schema tests only
pytest tests/unit/storage/test_schema.py -v
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
git add pyproject.toml src/storage/ tests/unit/storage/ docs/issue_6_pgvector_schema.md
git commit -m "feat(storage): design pgvector schema and migrations (#6)"

# Push branch
git push -u origin feature/issue-6-pgvector-schema

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(storage): design pgvector schema and migrations (#6)" \
  --body "Closes #6.
- Added \`psycopg[binary]>=3.1.18\` and \`pgvector>=0.3.0\` dependencies.
- Created initial migration script with \`documents\`, \`chunks\`, and \`embeddings\` tables.
- Added HNSW vector index on \`embeddings.embedding\` using \`vector_cosine_ops\`.
- Implemented migration runner utility in \`src/storage/migration_runner.py\`.
- Added unit tests verifying schema integrity, SQL definitions, and migration logic (coverage >= 90%)."
```

---

## Closing Criteria

- [ ] `pytest tests/unit/storage/ --cov-fail-under=90` passes with no errors.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #6`.
