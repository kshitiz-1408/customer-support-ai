import pytest
import json
import os
from evaluation.evaluate_answers import run_deterministic_eval

def test_benchmark_schema_validation():
    # Load and validate the answer_benchmark.json schema
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    benchmark_path = os.path.join(backend_dir, "evaluation", "answer_benchmark.json")
    
    assert os.path.exists(benchmark_path)
    
    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark = json.load(f)
        
    assert isinstance(benchmark, list)
    assert len(benchmark) >= 25
    
    for case in benchmark:
        assert "id" in case
        assert "query" in case
        assert "category" in case
        assert "answerable" in case
        
        assert isinstance(case["id"], str)
        assert isinstance(case["query"], str)
        assert isinstance(case["answerable"], bool)
        
        if case["answerable"]:
            assert "expected_topic" in case
            assert "reference_facts" in case
            assert isinstance(case["reference_facts"], list)
            for fact in case["reference_facts"]:
                assert "fact_id" in fact
                assert "fact" in fact
                assert "source" in fact
                assert "section" in fact


def test_deterministic_eval_metrics():
    # Test case 1: Fully Grounded Answer
    query = "How long is standard shipping?"
    answer = "Standard shipping takes 3 to 5 business days."
    reference_facts = [{
        "fact_id": "ship_1",
        "fact": "Standard Ground Shipping delivery takes 3 to 5 business days.",
        "source": "sample_kb.md",
        "section": "Shipping"
    }]
    
    eval_res = run_deterministic_eval(query, answer, True, reference_facts)
    assert len(eval_res["claims"]) > 0
    # The default deterministic mock rules mark answerable claims as SUPPORTED
    assert all(c["status"] == "SUPPORTED" for c in eval_res["claims"])
    assert eval_res["abstention"] == "NOT_APPLICABLE"
    assert eval_res["fact_coverage"][0]["status"] == "COVERED"


def test_deterministic_eval_incorrect_abstention():
    # Test case 2: Incorrect abstention (refusal on answerable)
    query = "How long is standard shipping?"
    answer = "I apologize, but I could not formulate an answer right now. Please try again."
    reference_facts = [{
        "fact_id": "ship_1",
        "fact": "Standard Ground Shipping delivery takes 3 to 5 business days.",
        "source": "sample_kb.md",
        "section": "Shipping"
    }]
    
    eval_res = run_deterministic_eval(query, answer, True, reference_facts)
    assert eval_res["abstention"] == "INCORRECT_ABSTENTION"
    assert eval_res["fact_coverage"][0]["status"] == "NOT_COVERED"


def test_deterministic_eval_correct_abstention():
    # Test case 3: Correct abstention (abstention on unanswerable)
    query = "Do you ship via drone?"
    answer = "I am sorry, but I do not have enough information to answer your question."
    reference_facts = []
    
    eval_res = run_deterministic_eval(query, answer, False, reference_facts)
    assert eval_res["abstention"] == "CORRECT_ABSTENTION"


def test_deterministic_eval_zero_claim_answer():
    # Test case 4: Zero-claim answer (empty generated string)
    query = "What is the Premium Plan?"
    answer = ""
    reference_facts = []
    
    eval_res = run_deterministic_eval(query, answer, True, reference_facts)
    assert len(eval_res["claims"]) == 0
    assert len(eval_res["fact_coverage"]) == 0


def test_no_secrets_in_answer_report():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(backend_dir, "knowledge_base", "answer_evaluation_report.json")
    
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "GEMINI_API_KEY" not in content
            assert "mongodb+srv" not in content
            assert "PASTE_YOUR_ACTUAL_API_KEY_HERE" not in content
