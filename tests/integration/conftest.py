"""Pytest configuration and fixtures for integration tests."""

import os
from collections.abc import Generator

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from src.storage.migration_runner import apply_migrations
from src.storage.vector_store import _build_default_connection_string


@pytest.fixture(scope="session", autouse=True)
def pgvector_db() -> Generator[PostgresContainer, None, None]:
    """
    Start a Postgres container with pgvector installed for integration tests.
    Sets environment variables so that the application connects to this container.
    """
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        # Override environment variables to point to the testcontainer
        os.environ["POSTGRES_HOST"] = str(postgres.get_container_host_ip())
        os.environ["POSTGRES_PORT"] = str(postgres.get_exposed_port(5432))
        os.environ["POSTGRES_DB"] = str(postgres.dbname)
        os.environ["POSTGRES_USER"] = str(postgres.username)
        os.environ["POSTGRES_PASSWORD"] = str(postgres.password)

        # Run database migrations
        conninfo = _build_default_connection_string()
        with psycopg.connect(conninfo) as conn:
            apply_migrations(conn)

        yield postgres
