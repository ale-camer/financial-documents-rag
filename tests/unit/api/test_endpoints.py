"""Unit tests for FastAPI endpoints."""

import os
import uuid
from unittest.mock import AsyncMock

os.environ["OPENAI_API_KEY"] = "test-key"

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_rag_pipeline
from src.api.main import app
from src.rag.models import RetrievedChunk


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient instance for the FastAPI app."""
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    """Verify the /health endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_query_endpoint_missing_query(client: TestClient) -> None:
    """Verify validation error when query is missing."""
    response = client.post("/query", json={})
    assert response.status_code == 422
    assert "query" in response.text


def test_query_endpoint_success(client: TestClient) -> None:
    """Verify /query correctly calls the pipeline and returns 200 with the answer."""
    mock_chunk = RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="Test content",
        section_name="Test section",
        chunk_index=0,
        similarity=0.9,
        document_metadata={},
    )

    mock_pipeline = AsyncMock()
    mock_pipeline.ask.return_value = {
        "answer": "This is a test answer.",
        "source_documents": [mock_chunk],
    }

    app.dependency_overrides[get_rag_pipeline] = lambda: mock_pipeline

    response = client.post("/query", json={"query": "Test query?"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is a test answer."
    assert len(data["source_documents"]) == 1
    assert data["source_documents"][0]["content"] == "Test content"
