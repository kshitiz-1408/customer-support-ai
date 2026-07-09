import pytest
import json
import os
from evaluation.evaluate_retrieval import dcg_at_k, ndcg_at_k

# Dummy content map and data for unit tests
def test_dcg_at_k():
    # dcg = 2 / log2(2) + 1 / log2(3) + 0 = 2.0 + 1.0 / 1.58496 = 2.6309
    relevances = [2, 1, 0]
    score = dcg_at_k(relevances, k=3)
    assert abs(score - 2.6309) < 0.001


def test_ndcg_at_k_normal():
    # Perfect match with ideal structure: DCG = IDCG, nDCG = 1.0
    relevances = [2, 1, 1]
    expected_count = 1
    score = ndcg_at_k(relevances, expected_count, k=3)
    assert abs(score - 1.0) < 0.001
    
    # Sub-perfect because rank 3 has no partially relevant context (relevance = 0)
    relevances_sub = [2, 1, 0]
    score_sub = ndcg_at_k(relevances_sub, expected_count, k=3)
    assert abs(score_sub - 0.8403) < 0.001


def test_ndcg_at_k_imperfect():
    # Expected highly relevant is at rank 2: relevances = [1, 2, 0]
    # dcg = 1 / log2(2) + 2 / log2(3) = 1.0 + 1.2618 = 2.2618
    # idcg = 2 / log2(2) + 1 / log2(3) + 1 / log2(4) = 3.1309
    # ndcg = 2.2618 / 3.1309 = 0.7224
    relevances = [1, 2, 0]
    expected_count = 1
    score = ndcg_at_k(relevances, expected_count, k=3)
    assert abs(score - 0.7224) < 0.001



def test_ndcg_at_k_zero_relevance():
    relevances = [0, 0, 0]
    score = ndcg_at_k(relevances, expected_count=2, k=3)
    assert score == 0.0


def test_benchmark_schema_validation():
    # Load and validate the retrieval_benchmark.json schema
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    benchmark_path = os.path.join(backend_dir, "evaluation", "retrieval_benchmark.json")
    
    assert os.path.exists(benchmark_path)
    
    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark = json.load(f)
        
    assert isinstance(benchmark, list)
    assert len(benchmark) >= 25
    
    for case in benchmark:
        assert "id" in case
        assert "query" in case
        assert "expected_topic" in case
        assert "expected_sources" in case
        assert "expected_section" in case
        assert "expected_chunks" in case
        assert "category" in case
        assert "difficulty" in case
        
        # Check type types
        assert isinstance(case["id"], str)
        assert isinstance(case["query"], str)
        assert isinstance(case["expected_sources"], list)
        assert isinstance(case["expected_chunks"], list)
        assert case["difficulty"] in ["easy", "medium", "hard", "unanswerable"]


def test_no_secrets_in_evaluation_output():
    # Verify no secrets exist in the evaluation report
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(backend_dir, "knowledge_base", "evaluation_report.json")
    
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Simple checks for common secret keywords
            assert "GEMINI_API_KEY" not in content
            assert "PASTE_YOUR_ACTUAL_API_KEY_HERE" not in content
            assert "mongodb+srv" not in content
