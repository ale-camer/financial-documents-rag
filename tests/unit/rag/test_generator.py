"""Unit tests for RAG generation and pipeline orchestration."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.rag.generator import RAGGenerator
from src.rag.models import RetrievedChunk
from src.rag.pipeline import RAGPipeline
from src.rag.retriever import HybridRetriever


@pytest.fixture
def mock_retrieved_chunks() -> list[RetrievedChunk]:
    """Provide sample retrieved chunks for testing."""
    import uuid

    return [
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            content="Sample risk factor content.",
            section_name="Risk Factors",
            chunk_index=0,
            similarity=0.9,
            document_metadata={"ticker": "AAPL"},
        )
    ]


def test_generator_initialization() -> None:
    """Verify ChatOpenAI is correctly initialized with gpt-4o-mini."""
    with patch("src.rag.generator.ChatOpenAI") as mock_chat:
        generator = RAGGenerator(llm_model="gpt-4o-mini", temperature=0.5)

        mock_chat.assert_called_once_with(model="gpt-4o-mini", temperature=0.5)
        assert generator.llm == mock_chat.return_value


@pytest.mark.asyncio
async def test_generate_answer_success(
    mock_retrieved_chunks: list[RetrievedChunk],
) -> None:
    """Verify the LCEL chain runs and returns a valid string."""
    with patch("src.rag.generator.ChatOpenAI"):
        generator = RAGGenerator()

        with patch(
            "langchain_core.runnables.RunnableSequence.ainvoke",
            new_callable=AsyncMock,
        ) as mock_ainvoke:
            mock_ainvoke.return_value = "This is the mocked answer."
            answer = await generator.generate_answer(
                "What is the risk?", mock_retrieved_chunks
            )

            assert answer == "This is the mocked answer."
            mock_ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_astream_answer_success(
    mock_retrieved_chunks: list[RetrievedChunk],
) -> None:
    """Verify that astream_answer correctly yields string chunks from the LLM."""
    with patch("src.rag.generator.ChatOpenAI"):
        generator = RAGGenerator()

        async def mock_astream(
            *args: object, **kwargs: object
        ) -> AsyncGenerator[str, None]:
            yield "This "
            yield "is "
            yield "streamed."

        with patch(
            "langchain_core.runnables.RunnableSequence.astream",
            side_effect=mock_astream,
        ):
            chunks = []
            async for chunk in generator.astream_answer(
                "What is the risk?", mock_retrieved_chunks
            ):
                chunks.append(chunk)

            assert chunks == ["This ", "is ", "streamed."]


@pytest.mark.asyncio
async def test_rag_pipeline_ask(
    mock_retrieved_chunks: list[RetrievedChunk],
) -> None:
    """Verify the orchestrator correctly pipes retrieved chunks into the generator."""
    mock_retriever = MagicMock(spec=HybridRetriever)
    mock_retriever.retrieve = AsyncMock(return_value=mock_retrieved_chunks)

    mock_generator = MagicMock(spec=RAGGenerator)
    mock_generator.generate_answer = AsyncMock(
        return_value="Pipeline generated answer."
    )

    pipeline = RAGPipeline(retriever=mock_retriever, generator=mock_generator)

    result = await pipeline.ask("Pipeline query?", filters={"ticker": "AAPL"})

    assert result["answer"] == "Pipeline generated answer."
    assert result["source_documents"] == mock_retrieved_chunks

    mock_retriever.retrieve.assert_awaited_once_with(
        "Pipeline query?", filters={"ticker": "AAPL"}
    )
    mock_generator.generate_answer.assert_awaited_once_with(
        "Pipeline query?", mock_retrieved_chunks
    )
