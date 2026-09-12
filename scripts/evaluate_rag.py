"""Basic evaluation script for the RAG pipeline using LangSmith."""

import asyncio
import logging
import os
import sys

# Ensure src is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.generator import RAGGenerator
from src.rag.pipeline import RAGPipeline
from src.rag.retriever import HybridRetriever
from src.storage.vector_store import VectorStoreClient


async def evaluate() -> None:
    """Run a basic evaluation of the RAG pipeline."""
    print("Setting up RAG Pipeline for evaluation...")
    logging.basicConfig(level=logging.INFO)

    # LangSmith tracing is automatically enabled if LANGCHAIN_TRACING_V2=true
    # and LANGCHAIN_API_KEY is provided in the environment.

    vector_store = VectorStoreClient()

    # Connect to vector store
    await vector_store.open()

    try:
        retriever = HybridRetriever(vector_store)
        generator = RAGGenerator()
        pipeline = RAGPipeline(retriever=retriever, generator=generator)

        test_questions = [
            "What are the main risk factors mentioned in the latest 10-K?",
            "How did the company's revenue change compared to the previous year?",
            "What is the company's strategy for growth?",
        ]

        for q in test_questions:
            print(f"\n[{'='*50}]")
            print(f"Question: {q}")

            try:
                result = await pipeline.ask(query=q)
                print(f"\nAnswer:\n{result['answer']}")

                print(f"\nRetrieved Documents ({len(result['source_documents'])} chunks):")
                for doc in result["source_documents"]:
                    section = doc.section_name or "Unknown"
                    print(
                        f" - [Document {doc.document_id}] Section: {section} "
                        f"(Similarity: {doc.similarity:.2f})"
                    )
            except Exception as e:
                print(f"Error evaluating question: {e}")

    finally:
        await vector_store.close()
        print("\nEvaluation complete.")


if __name__ == "__main__":
    asyncio.run(evaluate())
