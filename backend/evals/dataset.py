"""Golden JSON loader and DeepEval LLMTestCase construction for scrutiny benchmarks."""
import os
import json
from typing import List
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset

GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(__file__), "golden_dataset.json")


def load_raw_golden_data() -> List[dict]:
    """Loads raw golden test cases from JSON file."""
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_deepeval_dataset(agent_results: dict = None) -> EvaluationDataset:
    """Builds a DeepEval EvaluationDataset with LLMTestCases mapped from the golden dataset.
    
    If agent_results are provided (keyed by filename or case id), the actual output
    from the agent is injected into each test case for evaluation.
    """
    raw_data = load_raw_golden_data()
    test_cases = []

    for item in raw_data:
        pdf_name = item["pdf_name"]
        query = item["input_query"]
        expected_outputs = item["expected_outputs"]
        expected_str = json.dumps(expected_outputs, indent=2)
        retrieval_context = item.get("golden_context", [])

        # Default or actual output from agent run
        if agent_results and pdf_name in agent_results:
            actual = agent_results[pdf_name]
            if isinstance(actual, dict):
                actual_str = json.dumps(actual, indent=2)
            else:
                actual_str = str(actual)
        else:
            actual_str = expected_str  # For dry-run initialization

        meta_dict = {
            "pdf_name": pdf_name,
            "expected_doc_type": item.get("expected_doc_type"),
            "expected_outputs": expected_outputs
        }
        try:
            tc = LLMTestCase(
                input=query,
                actual_output=actual_str,
                expected_output=expected_str,
                retrieval_context=retrieval_context,
                context=retrieval_context,
                name=item["id"],
                metadata=meta_dict,
            )
        except TypeError:
            tc = LLMTestCase(
                input=query,
                actual_output=actual_str,
                expected_output=expected_str,
                retrieval_context=retrieval_context,
                context=retrieval_context,
                name=item["id"],
                additional_metadata=meta_dict,
            )
        test_cases.append(tc)

    dataset = EvaluationDataset()
    dataset.test_cases = test_cases
    return dataset
