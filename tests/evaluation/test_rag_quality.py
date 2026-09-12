"""Unit tests for the RAG evaluation framework."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from scripts.evaluate_rag import predict_rag_answer


def test_dataset_format() -> None:
    """Verify that the evaluation dataset has the correct structure."""
    dataset_path = Path("tests/evaluation/dataset.json")
    assert dataset_path.exists(), "Dataset file is missing"

    with open(dataset_path, encoding="utf-8") as f:
        examples = json.load(f)

    assert isinstance(examples, list)
    for ex in examples:
        assert "question" in ex
        assert "ground_truth" in ex
        assert "context" in ex


@pytest.mark.asyncio
@patch("scripts.evaluate_rag.get_rag_pipeline")
async def test_predict_rag_answer(mock_get_rag_pipeline: AsyncMock) -> None:
    """Test that the prediction wrapper calls the RAG pipeline correctly."""
    # Setup mock pipeline
    mock_pipeline = AsyncMock()
    mock_pipeline.ask.return_value = {"answer": "Mocked generated answer"}
    mock_get_rag_pipeline.return_value = mock_pipeline

    # Run prediction
    inputs = {"question": "¿Cuáles son los riesgos?"}
    result = await predict_rag_answer(inputs)

    # Assertions
    mock_pipeline.ask.assert_called_once_with(
        query="¿Cuáles son los riesgos?", filters=None
    )
    assert result == {"answer": "Mocked generated answer"}
