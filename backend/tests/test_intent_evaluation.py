import pytest
import json
import os
from evaluation.evaluate_intents import calculate_metrics, get_confusion_matrix
from agents.intent_detector import detect_intent

def test_intent_benchmark_schema_validation():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    benchmark_path = os.path.join(backend_dir, "evaluation", "intent_benchmark.json")
    
    assert os.path.exists(benchmark_path)
    
    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark = json.load(f)
        
    assert isinstance(benchmark, list)
    assert len(benchmark) >= 50
    
    for case in benchmark:
        assert "id" in case
        assert "query" in case
        assert "expected_intent" in case
        assert "expected_agent" in case
        assert "difficulty" in case
        assert "category" in case
        
        assert isinstance(case["id"], str)
        assert isinstance(case["query"], str)
        assert isinstance(case["expected_intent"], str)
        assert isinstance(case["expected_agent"], str)
        assert isinstance(case["difficulty"], str)
        assert isinstance(case["category"], str)


def test_intent_metrics_calculations():
    # Test helper metric formulas
    y_true = ["billing", "billing", "technical", "faq"]
    y_pred = ["billing", "technical", "technical", "faq"]
    classes = ["billing", "technical", "faq"]
    
    per_class, accuracy, macro_prec, macro_rec, macro_f1, weighted_f1 = calculate_metrics(
        y_true, y_pred, classes
    )
    
    assert accuracy == 0.75
    # For billing: TP=1, FP=0, FN=1 -> Prec=1.0, Rec=0.5, F1=0.666...
    assert per_class["billing"]["precision"] == 1.0
    assert per_class["billing"]["recall"] == 0.5
    
    # Check confusion matrix
    cm = get_confusion_matrix(y_true, y_pred, classes)
    assert cm["billing"]["billing"] == 1
    assert cm["billing"]["technical"] == 1
    assert cm["billing"]["faq"] == 0


def test_intent_normalization_rules():
    # Test case sensitivity and whitespace handling
    res_lower = detect_intent("i want a refund")
    res_upper = detect_intent("I WANT A REFUND")
    res_spaces = detect_intent("   i want a refund   ")
    res_punc = detect_intent("i want a refund!!!")
    
    assert res_lower["intent"] == "billing"
    assert res_upper["intent"] == "billing"
    assert res_spaces["intent"] == "billing"
    assert res_punc["intent"] == "billing"


def test_intent_precedence_and_fallback():
    # Precedence rule check: billing has precedence over other terms
    res_prec = detect_intent("I need technical support for my refund request")
    assert res_prec["intent"] == "billing"
    
    # Fallback to unknown intent
    res_fallback = detect_intent("gibberish random 12345 xyz")
    assert res_fallback["intent"] == "unknown"


def test_no_secrets_in_intent_report():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(backend_dir, "knowledge_base", "intent_evaluation_report.json")
    
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "GEMINI_API_KEY" not in content
            assert "mongodb+srv" not in content
