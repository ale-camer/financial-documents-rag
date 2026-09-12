"""Evaluation script for RAG quality using LangSmith."""

import asyncio
import json
import os
import sys
from pathlib import Path

from langsmith import Client
from langsmith.evaluation import evaluate
from src.api.dependencies import get_rag_pipeline


async def predict_rag_answer(inputs: dict) -> dict:
    """Run the RAG pipeline for a given question."""
    pipeline = get_rag_pipeline()
    question = inputs["question"]
    # We use empty filters for generic evaluation
    result = await pipeline.ask(query=question, filters=None)
    return {"answer": result["answer"]}


def run_evaluation() -> None:
    """Run the LangSmith evaluation."""
    # Ensure API keys are set
    if not os.getenv("LANGCHAIN_API_KEY") or not os.getenv("OPENAI_API_KEY"):
        print("Error: LANGCHAIN_API_KEY and OPENAI_API_KEY must be set.")
        sys.exit(1)

    # Load the ground truth dataset
    dataset_path = Path("tests/evaluation/dataset.json")
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}")
        sys.exit(1)

    with open(dataset_path, "r", encoding="utf-8") as f:
        examples = json.load(f)

    client = Client()
    dataset_name = "Financial RAG Evals"

    # Create dataset in LangSmith if it doesn't exist
    try:
        client.read_dataset(dataset_name=dataset_name)
        print(f"Dataset '{dataset_name}' already exists in LangSmith.")
    except Exception:
        print(f"Creating dataset '{dataset_name}' in LangSmith...")
        dataset = client.create_dataset(dataset_name=dataset_name)
        for ex in examples:
            client.create_example(
                inputs={"question": ex["question"]},
                outputs={"ground_truth": ex["ground_truth"]},
                dataset_id=dataset.id,
            )

    # Define a simple custom evaluator
    def llm_judge(run, example) -> dict:
        """Evaluate if the answer matches ground truth."""
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            expected = example.outputs.get("ground_truth", "")
            actual = run.outputs.get("answer", "")
            prompt = (
                f"Expected Answer: {expected}\n"
                f"Actual Answer: {actual}\n"
                "Does the actual answer contain the core information of the expected answer? "
                "Reply ONLY with YES or NO."
            )
            response = llm.invoke(prompt)
            score = 1 if "YES" in response.content.upper() else 0
            return {"key": "correctness", "score": score}
        except Exception as e:
            print(f"Evaluator error: {e}")
            return {"key": "correctness", "score": 0}

    # Wrap the async predict function in a sync wrapper for the evaluate function
    def sync_predict(inputs: dict) -> dict:
        return asyncio.run(predict_rag_answer(inputs))

    # Run evaluation
    print("Starting evaluation...")
    evaluate(
        sync_predict,
        data=dataset_name,
        evaluators=[llm_judge],
        experiment_prefix="rag-quality-test",
    )
    print("Evaluation completed! Check your LangSmith dashboard.")


if __name__ == "__main__":
    run_evaluation()
