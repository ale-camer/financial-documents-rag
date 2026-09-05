"""Database migration runner for PostgreSQL and pgvector schema."""

from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_migrations_dir() -> Path:
    """Return the filesystem path to the migrations directory."""
    return MIGRATIONS_DIR


def ensure_migrations_table(
    conn: psycopg.Connection[tuple[object, ...]],
) -> None:
    """Create the schema_migrations tracking table if it does not exist."""
    sql = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version VARCHAR(255) PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def get_applied_migrations(
    conn: psycopg.Connection[tuple[object, ...]],
) -> list[str]:
    """Retrieve the list of applied migration versions in ascending order."""
    ensure_migrations_table(conn)
    sql = "SELECT version FROM schema_migrations ORDER BY version ASC;"
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return [str(row[0]) for row in rows]


def apply_migrations(
    conn: psycopg.Connection[tuple[object, ...]],
) -> list[str]:
    """Apply all pending SQL migrations in alphanumeric order.

    Returns the list of migration versions applied during this run.
    """
    applied = set(get_applied_migrations(conn))
    migrations_dir = get_migrations_dir()

    migration_files = sorted(
        [f for f in migrations_dir.glob("*.sql") if not f.name.endswith(".down.sql")],
        key=lambda f: f.name,
    )

    newly_applied: list[str] = []

    for file_path in migration_files:
        version = file_path.stem
        if version in applied:
            continue

        sql_content = file_path.read_text(encoding="utf-8")
        try:
            with conn.cursor() as cur:
                cur.execute(sql_content)
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s);",
                    (version,),
                )
            conn.commit()
            newly_applied.append(version)
        except Exception:
            conn.rollback()
            raise

    return newly_applied


def rollback_migration(
    conn: psycopg.Connection[tuple[object, ...]],
    version: str,
) -> bool:
    """Roll back a specific migration version using its .down.sql script.

    Returns True if the migration was rolled back, False if it was not applied.
    """
    applied = set(get_applied_migrations(conn))

    if version not in applied:
        return False

    migrations_dir = get_migrations_dir()
    down_file = migrations_dir / f"{version}.down.sql"
    if not down_file.exists():
        raise FileNotFoundError(
            f"Down migration file not found for version: {version!r} at {down_file}"
        )

    sql_content = down_file.read_text(encoding="utf-8")
    try:
        with conn.cursor() as cur:
            cur.execute(sql_content)
            cur.execute(
                "DELETE FROM schema_migrations WHERE version = %s;",
                (version,),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
