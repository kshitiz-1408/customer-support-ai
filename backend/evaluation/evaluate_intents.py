import os
import json
import time
import sys
import re
from typing import List, Dict, Any, Tuple

# Resolve backend path and import intent_detector
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agents.intent_detector import detect_intent
from config.config import settings

BENCHMARK_PATH = os.path.join(backend_dir, "evaluation", "intent_benchmark.json")


def detect_intent_variant(query: str, variant: str) -> dict:
    q_lower = query.lower()
    
    billing_keywords = ["refund", "billing", "invoice", "payment", "payments", "pay", "paid", "charge", "charged", "card", "credit card", "debit card", "receipt", "billing statement", "subscription payment"]
    technical_keywords = ["error", "errors", "bug", "bugs", "crash", "crashes", "login", "log in", "password", "server", "port", "api", "integration", "webhook", "failed", "failure", "issue", "problem", "cannot", "can't", "not working", "broken"]
    product_keywords = ["product", "products", "price", "prices", "pricing", "cost", "costs", "subscription", "subscriptions", "plan", "plans", "premium", "feature", "features", "spec", "specs", "specification", "specifications", "version", "release", "release date", "buy", "purchase", "available", "availability", "compare", "comparison", "upgrade", "license"]
    complaint_keywords = ["complaint", "complain", "bad", "terrible", "worst", "poor", "unhappy", "angry", "frustrated", "disappointed", "escalate", "grievance", "manager", "supervisor"]
    faq_keywords = ["faq", "hours", "working hours", "office", "address", "location", "contact", "support", "email", "phone", "website", "how do i", "how to", "where is", "what is", "warranty", "warranties", "shipping", "shipment", "delivery", "delivered", "tracking", "track", "status", "package"]
    
    if variant == "precedence_swapped":
        # Precedence swapped order: complaint > billing > technical > product > faq
        order = [
            ("complaint", complaint_keywords),
            ("billing", billing_keywords),
            ("technical", technical_keywords),
            ("product", product_keywords),
            ("faq", faq_keywords)
        ]
        for intent_name, keywords in order:
            if any(k in q_lower for k in keywords):
                return {"intent": intent_name}
        return {"intent": "unknown"}
        
    elif variant == "regex_boundaries":
        order = [
            ("billing", billing_keywords),
            ("technical", technical_keywords),
            ("product", product_keywords),
            ("complaint", complaint_keywords),
            ("faq", faq_keywords)
        ]
        for intent_name, keywords in order:
            for k in keywords:
                if re.search(rf"\b{re.escape(k)}\b", q_lower):
                    return {"intent": intent_name}
        return {"intent": "unknown"}
        
    return {"intent": "unknown"}


def calculate_metrics(
    y_true: List[str], 
    y_pred: List[str], 
    classes: List[str]
) -> Tuple[Dict[str, Dict[str, float]], float, float, float, float]:
    per_class = {}
    total = len(y_true)
    
    for c in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == c and p == c)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != c and p == c)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == c and p != c)
        support = sum(1 for t in y_true if t == c)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        per_class[c] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support
        }
        
    macro_precision = sum(per_class[c]["precision"] for c in classes) / len(classes)
    macro_recall = sum(per_class[c]["recall"] for c in classes) / len(classes)
    macro_f1 = sum(per_class[c]["f1"] for c in classes) / len(classes)
    
    weighted_f1 = sum(per_class[c]["f1"] * per_class[c]["support"] for c in classes) / total if total > 0 else 0.0
    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / total if total > 0 else 0.0
    
    return per_class, accuracy, macro_precision, macro_recall, macro_f1, weighted_f1


def get_confusion_matrix(
    y_true: List[str], 
    y_pred: List[str], 
    classes: List[str]
) -> Dict[str, Dict[str, int]]:
    cm = {c: {o: 0 for o in classes} for c in classes}
    for t, p in zip(y_true, y_pred):
        if t in cm and p in cm[t]:
            cm[t][p] += 1
    return cm


def evaluate_intents() -> Dict[str, Any]:
    print(f"Loading intent benchmark from: {BENCHMARK_PATH}...")
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        benchmark = json.load(f)
        
    y_true = []
    y_pred = []
    
    agent_true = []
    agent_pred = []
    
    results = []
    classes = ["billing", "technical", "product", "complaint", "faq", "unknown"]
    
    agent_names = {
        "billing": "Billing Agent",
        "technical": "Technical Agent",
        "product": "Product Agent",
        "complaint": "Complaint Agent",
        "faq": "FAQ Agent",
        "unknown": "FAQ Agent"
    }
    
    errors = {
        "missing_keyword": 0,
        "vocabulary_mismatch": 0,
        "keyword_collision": 0,
        "precedence_issue": 0,
        "substring_false_positive": 0,
        "ambiguous_query": 0,
        "multi_intent_limitation": 0,
        "typo_noise": 0,
        "missing_context": 0,
        "wrong_intent_to_agent_mapping": 0,
        "duplicate_routing_implementation": 0,
        "benchmark_label_issue": 0
    }
    
    difficulty_stats = {
        "easy": {"total": 0, "correct": 0},
        "medium": {"total": 0, "correct": 0},
        "hard": {"total": 0, "correct": 0}
    }
    
    failed_cases = []
    
    for case in benchmark:
        case_id = case["id"]
        query = case["query"]
        expected_intent = case["expected_intent"]
        acceptable_intents = case.get("acceptable_intents", [expected_intent])
        expected_agent = case["expected_agent"]
        difficulty = case.get("difficulty", "easy")
        category = case.get("category", "")
        
        start_time = time.perf_counter()
        detect_res = detect_intent(query)
        latency = (time.perf_counter() - start_time) * 1000.0
        
        predicted_intent = detect_res["intent"]
        predicted_agent = agent_names.get(predicted_intent, "FAQ Agent")
        
        passed = (predicted_intent == expected_intent) or (predicted_intent in acceptable_intents)
        
        y_true.append(expected_intent)
        y_pred.append(predicted_intent)
        
        agent_true.append(expected_agent)
        agent_pred.append(predicted_agent)
        
        difficulty_stats[difficulty]["total"] += 1
        if predicted_intent == expected_intent:
            difficulty_stats[difficulty]["correct"] += 1
            
        case_result = {
            "id": case_id,
            "query": query,
            "expected_intent": expected_intent,
            "actual_intent": predicted_intent,
            "expected_agent": expected_agent,
            "actual_agent": predicted_agent,
            "passed": passed,
            "difficulty": difficulty,
            "category": category,
            "latency_ms": latency
        }
        results.append(case_result)
        
        if not passed:
            err_type = "vocabulary_mismatch"
            if category == "ambiguous":
                err_type = "ambiguous_query"
            elif category == "typo":
                err_type = "typo_noise"
            elif predicted_intent == "unknown":
                err_type = "missing_keyword"
            elif expected_intent in ["product", "complaint", "faq"] and predicted_intent in ["billing", "technical"]:
                err_type = "precedence_issue"
            elif "don't" in query.lower() or "not" in query.lower():
                err_type = "missing_context"
                
            errors[err_type] += 1
            
            failed_cases.append({
                "id": case_id,
                "query": query,
                "expected": expected_intent,
                "actual": predicted_intent,
                "agent_expected": expected_agent,
                "agent_actual": predicted_agent,
                "error_attribution": err_type
            })
            
    # Compute Metrics
    per_class, accuracy, macro_precision, macro_recall, macro_f1, weighted_f1 = calculate_metrics(
        y_true, y_pred, classes
    )
    
    agent_routing_accuracy = sum(1 for t, p in zip(agent_true, agent_pred) if t == p) / len(agent_true)
    
    cm = get_confusion_matrix(y_true, y_pred, classes)
    confusion_pairs = []
    for t in classes:
        for p in classes:
            if t != p and cm[t][p] > 0:
                confusion_pairs.append(((t, p), cm[t][p]))
    confusion_pairs.sort(key=lambda x: x[1], reverse=True)
    
    # Run Experiments (Phase 16)
    experiment_results = {}
    for var in ["precedence_swapped", "regex_boundaries"]:
        var_preds = []
        for case in benchmark:
            res = detect_intent_variant(case["query"], var)
            var_preds.append(res["intent"])
        _, var_acc, _, _, var_f1, _ = calculate_metrics(y_true, var_preds, classes)
        experiment_results[var] = {
            "accuracy": var_acc,
            "macro_f1": var_f1
        }
        
    report_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "benchmark_version": "1.0",
        "benchmark_size": len(benchmark),
        "aggregate_metrics": {
            "overall_accuracy": accuracy,
            "macro_precision": macro_precision,
            "macro_recall": macro_recall,
            "macro_f1": macro_f1,
            "weighted_f1": weighted_f1,
            "agent_routing_accuracy": agent_routing_accuracy,
            "failed_query_count": len(failed_cases)
        },
        "per_class_metrics": per_class,
        "confusion_matrix": cm,
        "difficulty_analysis": {
            d: (stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0)
            for d, stats in difficulty_stats.items()
        },
        "error_attribution": errors,
        "failed_cases": failed_cases,
        "experiments": experiment_results
    }
    
    report_path = os.path.join(backend_dir, "knowledge_base", "intent_evaluation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"Saved JSON report to: {report_path}")
    
    # Save human-readable Markdown summary report
    output_dir = getattr(settings, "EVALUATION_OUTPUT_DIR", None)
    if output_dir:
        md_dir = os.path.abspath(output_dir)
    else:
        md_dir = os.path.join(backend_dir, "evaluation_reports")
        
    os.makedirs(md_dir, exist_ok=True)
    md_path = os.path.join(md_dir, "day6_intent_report.md")
    
    cm_rows = ""
    for r in classes:
        row_str = f"| **{r}** | " + " | ".join(str(cm[r][c]) for c in classes) + " |"
        cm_rows += row_str + "\n"
        
    failed_table = ""
    for f in failed_cases[:10]:
        failed_table += f"| `{f['id']}` | '{f['query']}' | `{f['expected']}` | `{f['actual']}` | `{f['error_attribution']}` |\n"
        
    top_confusion_str = "None"
    if confusion_pairs:
        top_confusion_str = f"`{confusion_pairs[0][0][0]}` predicted as `{confusion_pairs[0][0][1]}` ({confusion_pairs[0][1]} times)"
    second_confusion_str = "None"
    if len(confusion_pairs) > 1:
        second_confusion_str = f"`{confusion_pairs[1][0][0]}` predicted as `{confusion_pairs[1][0][1]}` ({confusion_pairs[1][1]} times)"
        
    md_content = f"""# Day 6 — Intent-Detection and Agent-Routing Report

This report documents classification accuracy, routing correctness, and confusion metrics for the Multi-Agent Router.

---

## 📊 1. Intent Detection Performance Metrics

- **Benchmark Size**: {len(benchmark)}
- **Failed Queries**: {len(failed_cases)}

| Metric | Value |
| :--- | :---: |
| **Overall Accuracy** | **{accuracy:.4f}** |
| **Macro Precision** | {macro_precision:.4f} |
| **Macro Recall** | {macro_recall:.4f} |
| **Macro F1-Score** | {macro_f1:.4f} |
| **Weighted F1-Score** | {weighted_f1:.4f} |
| **Agent Routing Accuracy** | **{agent_routing_accuracy:.4f}** |

---

## 🗺️ 2. Confusion Matrix

| Expected \\ Predicted | billing | technical | product | complaint | faq | unknown |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
{cm_rows}
- **Top Confusion Pair**: {top_confusion_str}
- **Second Confusion Pair**: {second_confusion_str}

---

## 🎯 3. Error Analysis and Difficulty Breakdown

### Performance by Difficulty:
- **Easy**: {report_data['difficulty_analysis']['easy']:.4f}
- **Medium**: {report_data['difficulty_analysis']['medium']:.4f}
- **Hard**: {report_data['difficulty_analysis']['hard']:.4f}

### Error Attribution:
- **Keyword Collisions**: `{errors['keyword_collision']}`
- **Precedence Issues**: `{errors['precedence_issue']}`
- **Vocabulary Mismatches**: `{errors['vocabulary_mismatch']}`
- **Typo / Noisy Text**: `{errors['typo_noise']}`
- **Ambiguous Queries**: `{errors['ambiguous_query']}`

---

## 🔬 4. Improvement Experiments

We conducted safe offline intent detection experiments over the baseline:

| Experiment | Accuracy | Macro F1 | Delta (Accuracy) | Description |
| :--- | :---: | :---: | :---: | :--- |
| **Baseline Heuristics** | **{accuracy:.4f}** | **{macro_f1:.4f}** | *Ref* | Current production keywords & precedence order |
| **Precedence Swapping** | {experiment_results['precedence_swapped']['accuracy']:.4f} | {experiment_results['precedence_swapped']['macro_f1']:.4f} | **{experiment_results['precedence_swapped']['accuracy'] - accuracy:+.4f}** | complaint > billing > technical > product > faq |
| **Regex Word Boundaries** | {experiment_results['regex_boundaries']['accuracy']:.4f} | {experiment_results['regex_boundaries']['macro_f1']:.4f} | **{experiment_results['regex_boundaries']['accuracy'] - accuracy:+.4f}** | Match on exact word boundaries (\\bkeyword\\b) |

---

## ❌ 5. Top Failed Case Samples (First 10)

| Case ID | Query | Expected Intent | Predicted Intent | Error Category |
| :--- | :--- | :---: | :---: | :--- |
{failed_table}
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved Markdown summary report to: {md_path}")
    
    # Print metrics summary directly to stdout
    print("\n--- Intent Evaluation Metrics Summary ---")
    print(f"Benchmark Size                : {len(benchmark)}")
    print(f"Overall Accuracy              : {accuracy:.4f}")
    print(f"Macro Precision               : {macro_precision:.4f}")
    print(f"Macro Recall                  : {macro_recall:.4f}")
    print(f"Macro F1-Score                : {macro_f1:.4f}")
    print(f"Weighted F1-Score             : {weighted_f1:.4f}")
    print(f"Agent Routing Accuracy        : {agent_routing_accuracy:.4f}")
    print(f"Failed Query Count            : {len(failed_cases)}")
    print(f"Top Confusion                 : {top_confusion_str}")
    print("----------------------------------------")
    
    return report_data


if __name__ == "__main__":
    evaluate_intents()
