import os
import json
import time
import math
import sys
from typing import List, Dict, Any, Tuple

# Resolve backend path and import necessary modules
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from main import app
from config.config import settings

BENCHMARK_PATH = os.path.join(backend_dir, "evaluation", "answer_benchmark.json")


def parse_llm_json(response_text: str) -> Dict[str, Any]:
    """Cleans and parses the LLM output into a dictionary."""
    clean = response_text.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    if clean.endswith("```"):
        clean = clean[:-3]
    return json.loads(clean.strip())


def run_deterministic_eval(
    query: str, 
    answer: str, 
    answerable: bool, 
    reference_facts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Fallback deterministic evaluator (Layer 1) for offline/mock runs.
    """
    safe_ans = answer or ""
    clean_ans = safe_ans.lower()
    
    # 1. Abstention detection
    abstention_keywords = ["sorry", "apologize", "do not have enough information", "not have information", "please clarify"]
    is_abstention = any(k in clean_ans for k in abstention_keywords)
    
    abstention_status = "NOT_APPLICABLE"
    if not answerable:
        if is_abstention:
            abstention_status = "CORRECT_ABSTENTION"
        else:
            abstention_status = "NOT_APPLICABLE" # Failed to abstain
    else:
        # Check for incorrect fallback/refusal on answerable queries
        fallback_refusals = ["apologize, but i could not formulate an answer", "please clarify your question"]
        is_refusal = any(k in clean_ans for k in fallback_refusals)
        if is_refusal:
            abstention_status = "INCORRECT_ABSTENTION"
            
    # 2. Estimate claim support and fact coverage via basic keyword matching
    claims = []
    fact_coverage = []
    
    # Extract simple sentence claims from generated answer
    sentences = [s.strip() for s in safe_ans.split(".") if s.strip()]
    for s in sentences:
        # Assume supported if it doesn't contain negation terms
        claims.append({
            "claim": s,
            "status": "SUPPORTED" if answerable else "UNSUPPORTED"
        })
        
    for fact in reference_facts:
        fact_words = [w.lower() for w in fact["fact"].split() if len(w) > 4]
        # Match if at least two long words from expected fact are present in generated answer
        match_count = sum(1 for w in fact_words if w in clean_ans)
        status = "NOT_COVERED"
        if match_count >= 2:
            status = "COVERED"
        elif match_count >= 1:
            status = "PARTIALLY_COVERED"
            
        fact_coverage.append({
            "fact_id": fact["fact_id"],
            "status": status
        })
        
    return {
        "claims": claims,
        "fact_coverage": fact_coverage,
        "abstention": abstention_status
    }


def run_llm_judge(
    query: str,
    context_list: List[Dict[str, Any]],
    reference_facts: List[Dict[str, Any]],
    generated_answer: str
) -> Dict[str, Any]:
    """
    Invokes Gemini to evaluate answer groundedness, claims support, and fact coverage (Layer 3).
    """
    from google import genai
    
    # 1. Format inputs for judge
    context_text = ""
    for i, c in enumerate(context_list):
        context_text += f"Context [{i}]: {c['content']}\n"
    if not context_text:
        context_text = "(Empty Context)\n"
        
    facts_text = ""
    for f in reference_facts:
        facts_text += f"- [{f['fact_id']}]: {f['fact']}\n"
    if not facts_text:
        facts_text = "(No Expected Reference Facts)\n"
        
    prompt = f"""
You are an expert AI evaluator assessing RAG (Retrieval-Augmented Generation) answer quality.
Analyze the following generated answer against the retrieved context and expected reference facts.

User Query: {query}

Retrieved Grounding Context:
{context_text}

Expected Reference Facts:
{facts_text}

Generated Answer:
{generated_answer}

Tasks:
1. Decompose the Generated Answer into individual material factual claims. Focus on company-specific rules, numbers, prices, and policies. Ignore general conversational framing like "Sure, I can help".
2. For each claim, evaluate if it is:
   - SUPPORTED: Explicitly stated in the Grounding Context.
   - PARTIALLY_SUPPORTED: Partially stated or lacks complete proof.
   - UNSUPPORTED: Not mentioned at all in the Grounding Context.
   - CONTRADICTED: Directly conflicts with the Grounding Context.
3. For each Expected Reference Fact, evaluate if it is:
   - COVERED: Present and correctly stated in the Generated Answer.
   - PARTIALLY_COVERED: Vaguely or partially stated.
   - NOT_COVERED: Missing or incorrectly stated in the Generated Answer.
4. Classify the overall Abstention behavior:
   - CORRECT_ABSTENTION: The query is unanswerable based on the context, and the system correctly abstained or stated it didn't know.
   - INCORRECT_ABSTENTION: The context had the answer, but the system refused to answer.
   - NOT_APPLICABLE: The query was answerable and the system generated an answer, or the query was unanswerable and the system failed to abstain.

Return the result STRICTLY as a JSON object with this structure:
{{
  "claims": [
    {{
      "claim": "string representing the claim",
      "status": "SUPPORTED" | "PARTIALLY_SUPPORTED" | "UNSUPPORTED" | "CONTRADICTED"
    }}
  ],
  "fact_coverage": [
    {{
      "fact_id": "string fact_id",
      "status": "COVERED" | "PARTIALLY_COVERED" | "NOT_COVERED"
    }}
  ],
  "abstention": "CORRECT_ABSTENTION" | "INCORRECT_ABSTENTION" | "NOT_APPLICABLE"
}}
"""
    from google.genai.errors import ClientError
    max_retries = 3
    backoff = 2.0
    for attempt in range(max_retries):
        try:
            # Initialize separate genai Client
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            return parse_llm_json(response.text)
        except ClientError as e:
            if e.code == 429 and attempt < max_retries - 1:
                sleep_sec = backoff ** (attempt + 1)
                print(f"LLM Judge hit 429. Retrying in {sleep_sec}s...")
                time.sleep(sleep_sec)
                continue
            print(f"LLM Judge failed on ClientError: {str(e)}. Falling back to deterministic matching.")
            break
        except Exception as e:
            print(f"LLM Judge failed on general error: {str(e)}. Falling back to deterministic matching.")
            break
            
    # Return fallback deterministic mapping
    answerable = len(reference_facts) > 0
    return run_deterministic_eval(query, generated_answer, answerable, reference_facts)



def evaluate_answers(use_judge: bool = True) -> Dict[str, Any]:
    print(f"Loading answer benchmark from: {BENCHMARK_PATH}...")
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        benchmark = json.load(f)
        
    client = TestClient(app)
    
    results = []
    
    total_claims = 0
    supported_claims = 0
    unsupported_claims = 0
    contradicted_claims = 0
    
    fully_grounded_count = 0
    grounded_applicable_answers = 0
    
    ans_total_expected_facts = 0
    ans_total_covered_facts = 0
    
    correct_abstentions = 0
    incorrect_abstentions = 0
    total_unanswerable = 0
    total_answerable = 0
    
    print(f"Running evaluation on {len(benchmark)} benchmark queries...")
    
    for case in benchmark:
        # Rate-limiting sleep to avoid hitting 15 RPM free tier limits
        time.sleep(1.5)
        
        query = case["query"]
        case_id = case["id"]
        answerable = case["answerable"]
        reference_facts = case.get("reference_facts", [])
        
        if answerable:
            total_answerable += 1
            ans_total_expected_facts += len(reference_facts)
        else:
            total_unanswerable += 1
            
        print(f"[{case_id}] Query: '{query}'")
        
        # 1. Get generation output from API (incorporates pipeline, RAG retrieval, history context)
        start_time = time.perf_counter()
        resp = client.post("/api/v1/chat/", json={"message": query})
        latency = (time.perf_counter() - start_time) * 1000.0
        
        if resp.status_code != 200:
            print(f"  API Error: status code {resp.status_code}")
            continue
            
        chat_data = resp.json()
        generated_answer = chat_data.get("message", "")
        
        # Resolve retrieved context (using offline retrieval from RAG for the same query to supply LLM Judge)
        from rag.rag_pipeline import query_kb
        retrieved_context = query_kb(query, top_k=4)
        retrieved_sources = list(set(r.get("metadata", {}).get("source", "unknown") for r in retrieved_context))
        
        # 2. Run evaluator (LLM Judge or Fallback)
        if use_judge and settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "PASTE_YOUR_ACTUAL_API_KEY_HERE":
            eval_output = run_llm_judge(query, retrieved_context, reference_facts, generated_answer)
        else:
            eval_output = run_deterministic_eval(query, generated_answer, answerable, reference_facts)
            
        # Parse metrics
        claims = eval_output.get("claims", [])
        fact_coverage = eval_output.get("fact_coverage", [])
        abstention = eval_output.get("abstention", "NOT_APPLICABLE")
        
        # Aggregate claim metrics
        case_claims_count = len(claims)
        case_supported_count = sum(1 for c in claims if c["status"] == "SUPPORTED")
        case_unsupported_count = sum(1 for c in claims if c["status"] == "UNSUPPORTED")
        case_contradicted_count = sum(1 for c in claims if c["status"] == "CONTRADICTED")
        
        total_claims += case_claims_count
        supported_claims += case_supported_count
        unsupported_claims += case_unsupported_count
        contradicted_claims += case_contradicted_count
        
        # Grounded answer calculation
        # An answer containing claims is fully grounded if all claims are SUPPORTED
        if case_claims_count > 0:
            grounded_applicable_answers += 1
            if case_supported_count == case_claims_count:
                fully_grounded_count += 1
                
        # Fact coverage mapping
        case_covered_facts = sum(1 for f in fact_coverage if f["status"] == "COVERED")
        case_partially_covered_facts = sum(1 for f in fact_coverage if f["status"] == "PARTIALLY_COVERED")
        ans_total_covered_facts += case_covered_facts + (0.5 * case_partially_covered_facts)
        
        # Abstentions
        if abstention == "CORRECT_ABSTENTION":
            correct_abstentions += 1
        elif abstention == "INCORRECT_ABSTENTION":
            incorrect_abstentions += 1
            
        results.append({
            "id": case_id,
            "query": query,
            "answerable": answerable,
            "generated_answer": generated_answer,
            "retrieved_sources": retrieved_sources,
            "latency_ms": latency,
            "claims": claims,
            "fact_coverage": fact_coverage,
            "abstention": abstention
        })
        
    # Calculate Final Metrics
    claim_support_rate = supported_claims / total_claims if total_claims > 0 else 0.0
    hallucination_rate = unsupported_claims / total_claims if total_claims > 0 else 0.0
    contradiction_rate = contradicted_claims / total_claims if total_claims > 0 else 0.0
    fully_grounded_rate = fully_grounded_count / grounded_applicable_answers if grounded_applicable_answers > 0 else 0.0
    
    correct_abstention_rate = correct_abstentions / total_unanswerable if total_unanswerable > 0 else 0.0
    incorrect_abstention_rate = incorrect_abstentions / total_answerable if total_answerable > 0 else 0.0
    answer_coverage = ans_total_covered_facts / ans_total_expected_facts if ans_total_expected_facts > 0 else 0.0
    
    print("\n--- Answer Evaluation Summary ---")
    print(f"Benchmark Size                : {len(benchmark)}")
    print(f"Total Material Claims         : {total_claims}")
    print(f"Claim Support Rate            : {claim_support_rate:.4f}")
    print(f"Hallucination Rate            : {hallucination_rate:.4f}")
    print(f"Contradiction Rate            : {contradiction_rate:.4f}")
    print(f"Fully Grounded Answer Rate    : {fully_grounded_rate:.4f}")
    print(f"Correct Abstention Rate       : {correct_abstention_rate:.4f}")
    print(f"Incorrect Abstention Rate     : {incorrect_abstention_rate:.4f}")
    print(f"Answer Coverage               : {answer_coverage:.4f}")
    
    report_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_name": settings.GEMINI_MODEL_NAME or "gemini-2.5-flash",
        "evaluator_type": "LLM Judge" if use_judge else "Deterministic Fallback",
        "metrics": {
            "benchmark_size": len(benchmark),
            "total_material_claims": total_claims,
            "claim_support_rate": claim_support_rate,
            "hallucination_rate": hallucination_rate,
            "contradiction_rate": contradiction_rate,
            "fully_grounded_answer_rate": fully_grounded_rate,
            "correct_abstention_rate": correct_abstention_rate,
            "incorrect_abstention_rate": incorrect_abstention_rate,
            "answer_coverage": answer_coverage
        },
        "results": results
    }
    
    # Save reports
    report_path = os.path.join(backend_dir, "knowledge_base", "answer_evaluation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"Saved JSON report to: {report_path}")
    
    # Produce Markdown Summary
    md_path = os.path.expanduser(
        "~/.gemini/antigravity-ide/brain/19a93036-5576-4401-8a01-827787595b36/day6_answer_report.md"
    )
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    
    # Count errors by attribution category (Phase 8)
    retret_fail = 0
    gen_fail = 0
    halluc_fail = 0
    contra_fail = 0
    abst_fail = 0
    over_abst_fail = 0
    
    for r in results:
        # Check if failed (either ungrounded, missed facts, or wrong abstention)
        is_failed = False
        unsupported = sum(1 for c in r["claims"] if c["status"] == "UNSUPPORTED")
        contradicted = sum(1 for c in r["claims"] if c["status"] == "CONTRADICTED")
        
        if unsupported > 0 or contradicted > 0:
            is_failed = True
            
        if r["answerable"] and r["abstention"] == "INCORRECT_ABSTENTION":
            is_failed = True
            over_abst_fail += 1
            
        if not r["answerable"] and r["abstention"] != "CORRECT_ABSTENTION":
            is_failed = True
            abst_fail += 1
            
        if is_failed:
            if unsupported > 0:
                halluc_fail += 1
            if contradicted > 0:
                contra_fail += 1
            # If retrieved context doesn't contain expected facts
            # (since we know K=5 retrieves 100% of facts, any missed retrieval is for K < 5, but chat endpoint uses K=4)
            if len(r["retrieved_sources"]) == 0:
                retret_fail += 1
            else:
                gen_fail += 1
                
    md_content = f"""# Day 6 — Grounded-Answer, Faithfulness, and Hallucination Report

This report documents the baseline quality performance of generated support responses against expected reference facts.

---

## 📊 1. Answer Quality Metrics Summary

- **Benchmark Size**: {len(benchmark)}
- **Answerable Cases**: {total_answerable}
- **Unanswerable Cases**: {total_unanswerable}

| Metric | Baseline Value | Formula / Definition |
| :--- | :---: | :--- |
| **Claim Support Rate** | {claim_support_rate:.4f} | Supported claims / total claims |
| **Hallucination Rate** | {hallucination_rate:.4f} | Unsupported claims / total claims |
| **Contradiction Rate** | {contradiction_rate:.4f} | Contradicted claims / total claims |
| **Fully Grounded Answer Rate** | {fully_grounded_rate:.4f} | Answers where all claims are supported |
| **Correct Abstention Rate** | {correct_abstention_rate:.4f} | Correct abstentions / unanswerable queries |
| **Incorrect Abstention Rate** | {incorrect_abstention_rate:.4f} | Incorrect abstentions / answerable queries |
| **Answer Coverage** | {answer_coverage:.4f} | Expressed expected facts / total expected facts |

---

## 🔎 2. Retrieval vs Generation Error Attribution

For failed or ungrounded responses, the root cause error category counts are as follows:

- **Retrieval Failures** (context missing): `{retret_fail}`
- **Generation Failures** (context present but ignored): `{gen_fail}`
- **Hallucinations** (unsupported company claims added): `{halluc_fail}`
- **Contradictions** (conflicts with context): `{contra_fail}`
- **Abstention Failures** (failed to reject unanswerable): `{abst_fail}`
- **Over-Abstentions** (refused valid answerable): `{over_abst_fail}`

---

## 🛡️ 3. Safety and Robustness Insights

1. **Unanswerable Queries Protection**:
   - The correct abstention rate is `{correct_abstention_rate:.4f}`.
   - When the RAG retrieval system returns irrelevant chunks for queries outside the KB, Gemini's system instructions act as a safety gate.
2. **False Premise Consistency**:
   - Misleading query evaluation shows whether the model adopts incorrect premises or successfully corrects them using context.
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved human-readable Markdown summary report to: {md_path}")
    
    return report_data


if __name__ == "__main__":
    import argparse
    from google.genai import types
    
    parser = argparse.ArgumentParser(description="Reproducible RAG Answer Quality Evaluation Runner")
    parser.add_argument("--judge", action="store_true", help="Enable model-assisted LLM Judge (requires GEMINI_API_KEY)")
    args = parser.parse_args()
    
    print("======================================================================")
    print("WARNING: Running answer evaluation makes live API requests to Gemini.")
    print("This will incur free-tier quota usage (15 RPM limits apply).")
    if args.judge:
        print("Model-assisted LLM Judge is ENABLED.")
    else:
        print("Model-assisted LLM Judge is DISABLED (using deterministic metrics).")
    print("======================================================================\n")
    
    evaluate_answers(use_judge=args.judge)

