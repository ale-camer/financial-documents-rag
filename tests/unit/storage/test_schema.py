"""Unit tests for storage schema SQL definitions and migration runner."""

from typing import cast
from unittest.mock import MagicMock

import psycopg
import pytest

from src.storage.migration_runner import (
    apply_migrations,
    ensure_migrations_table,
    get_applied_migrations,
    get_migrations_dir,
    rollback_migration,
)


@pytest.fixture
def mock_cursor() -> MagicMock:
    """Provide a mock database cursor."""
    return MagicMock()


@pytest.fixture
def mock_conn(mock_cursor: MagicMock) -> psycopg.Connection[tuple[object, ...]]:
    """Provide a mock psycopg connection with a configured cursor context manager."""
    conn = MagicMock(spec=psycopg.Connection)
    conn.cursor.return_value.__enter__.return_value = mock_cursor
    return cast(psycopg.Connection[tuple[object, ...]], conn)


def test_migration_sql_files_exist() -> None:
    """Verify that migration up and down SQL files exist and are not empty."""
    migrations_dir = get_migrations_dir()
    up_file = migrations_dir / "001_initial_schema.sql"
    down_file = migrations_dir / "001_initial_schema.down.sql"

    assert up_file.exists(), f"Missing up migration file: {up_file}"
    assert down_file.exists(), f"Missing down migration file: {down_file}"
    assert len(up_file.read_text(encoding="utf-8").strip()) > 0
    assert len(down_file.read_text(encoding="utf-8").strip()) > 0


def test_documents_table_definition() -> None:
    """Verify documents table contains all required columns and constraints."""
    up_file = get_migrations_dir() / "001_initial_schema.sql"
    sql = up_file.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS documents" in sql
    assert "id UUID PRIMARY KEY DEFAULT gen_random_uuid()" in sql
    assert "cik VARCHAR(10) NOT NULL" in sql
    assert "ticker VARCHAR(10)" in sql
    assert "period VARCHAR(20) NOT NULL" in sql
    assert "form_type VARCHAR(10) NOT NULL DEFAULT '10-K'" in sql
    assert "accession_number VARCHAR(25) NOT NULL UNIQUE" in sql
    assert "ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()" in sql


def test_chunks_table_definition() -> None:
    """Verify chunks table contains required columns, check constraints, and FK."""
    up_file = get_migrations_dir() / "001_initial_schema.sql"
    sql = up_file.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS chunks" in sql
    assert "document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE" in sql
    assert "section_name VARCHAR(50) NOT NULL" in sql
    assert "content TEXT NOT NULL" in sql
    assert "token_count INTEGER NOT NULL CHECK (token_count >= 0)" in sql
    assert "chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0)" in sql
    assert "uq_chunks_document_chunk_index UNIQUE" in sql


def test_embeddings_table_definition() -> None:
    """Verify embeddings table has vector(1536) column and chunk_id FK."""
    up_file = get_migrations_dir() / "001_initial_schema.sql"
    sql = up_file.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS embeddings" in sql
    assert (
        "chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE UNIQUE" in sql
    )
    assert "embedding vector(1536) NOT NULL" in sql
    assert "model_name VARCHAR(50) NOT NULL DEFAULT 'text-embedding-3-small'" in sql


def test_hnsw_index_specification() -> None:
    """Verify HNSW index is created using vector_cosine_ops."""
    up_file = get_migrations_dir() / "001_initial_schema.sql"
    sql = up_file.read_text(encoding="utf-8")

    assert "CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON embeddings" in sql
    assert "USING hnsw (embedding vector_cosine_ops)" in sql


def test_rollback_sql_definitions() -> None:
    """Verify down migration drops all tables and index in reverse order."""
    down_file = get_migrations_dir() / "001_initial_schema.down.sql"
    sql = down_file.read_text(encoding="utf-8")

    assert "DROP INDEX IF EXISTS idx_embeddings_hnsw;" in sql
    assert "DROP TABLE IF EXISTS embeddings CASCADE;" in sql
    assert "DROP TABLE IF EXISTS chunks CASCADE;" in sql
    assert "DROP TABLE IF EXISTS documents CASCADE;" in sql


def test_ensure_migrations_table(
    mock_conn: psycopg.Connection[tuple[object, ...]],
    mock_cursor: MagicMock,
) -> None:
    """Verify ensure_migrations_table creates schema_migrations tracking table."""
    ensure_migrations_table(mock_conn)

    mock_cursor.execute.assert_called_once()
    sql_executed = mock_cursor.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS schema_migrations" in sql_executed
    cast(MagicMock, mock_conn).commit.assert_called_once()


def test_get_applied_migrations(
    mock_conn: psycopg.Connection[tuple[object, ...]],
    mock_cursor: MagicMock,
) -> None:
    """Verify get_applied_migrations returns list of version strings."""
    mock_cursor.fetchall.return_value = [("001_initial_schema",)]

    versions = get_applied_migrations(mock_conn)

    assert versions == ["001_initial_schema"]


def test_migration_runner_applies_unapplied(
    mock_conn: psycopg.Connection[tuple[object, ...]],
    mock_cursor: MagicMock,
) -> None:
    """Verify apply_migrations executes pending SQL files and records versions."""
    # No migrations applied yet
    mock_cursor.fetchall.return_value = []

    applied = apply_migrations(mock_conn)

    assert "001_initial_schema" in applied
    assert cast(MagicMock, mock_conn).commit.call_count >= 1


def test_migration_runner_skips_already_applied(
    mock_conn: psycopg.Connection[tuple[object, ...]],
    mock_cursor: MagicMock,
) -> None:
    """Verify apply_migrations does not re-apply already executed migrations."""
    mock_cursor.fetchall.return_value = [("001_initial_schema",)]

    applied = apply_migrations(mock_conn)

    assert applied == []


def test_migration_runner_apply_error_triggers_rollback(
    mock_conn: psycopg.Connection[tuple[object, ...]],
    mock_cursor: MagicMock,
) -> None:
    """Verify transaction rollback on SQL execution error during apply."""
    mock_cursor.fetchall.return_value = []
    mock_cursor.execute.side_effect = [
        None,  # ensure_migrations_table
        None,  # SELECT version
        psycopg.Error("Database syntax error"),
    ]

    with pytest.raises(psycopg.Error, match="Database syntax error"):
        apply_migrations(mock_conn)

    cast(MagicMock, mock_conn).rollback.assert_called_once()


def test_migration_runner_rollback_success(
    mock_conn: psycopg.Connection[tuple[object, ...]],
    mock_cursor: MagicMock,
) -> None:
    """Verify rollback_migration executes down SQL and removes version."""
    mock_cursor.fetchall.return_value = [("001_initial_schema",)]

    result = rollback_migration(mock_conn, "001_initial_schema")

    assert result is True
    cast(MagicMock, mock_conn).commit.assert_called()


def test_migration_runner_rollback_not_applied(
    mock_conn: psycopg.Connection[tuple[object, ...]],
    mock_cursor: MagicMock,
) -> None:
    """Verify rollback_migration returns False when migration is not applied."""
    mock_cursor.fetchall.return_value = []

    result = rollback_migration(mock_conn, "001_initial_schema")

    assert result is False


def test_migration_runner_rollback_missing_file(
    mock_conn: psycopg.Connection[tuple[object, ...]],
    mock_cursor: MagicMock,
) -> None:
    """Verify rollback raises FileNotFoundError when down script is missing."""
    mock_cursor.fetchall.return_value = [("non_existent_version",)]

    with pytest.raises(FileNotFoundError, match="Down migration file not found"):
        rollback_migration(mock_conn, "non_existent_version")


def test_migration_runner_rollback_error_triggers_rollback(
    mock_conn: psycopg.Connection[tuple[object, ...]],
    mock_cursor: MagicMock,
) -> None:
    """Verify transaction rollback on SQL error during rollback."""
    mock_cursor.fetchall.return_value = [("001_initial_schema",)]
    mock_cursor.execute.side_effect = [
        None,  # ensure_migrations_table
        None,  # SELECT version
        psycopg.Error("Rollback error"),
    ]

    with pytest.raises(psycopg.Error, match="Rollback error"):
        rollback_migration(mock_conn, "001_initial_schema")

    cast(MagicMock, mock_conn).rollback.assert_called_once()
