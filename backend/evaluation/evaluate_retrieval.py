import os
import json
import time
import math
import statistics
from typing import List, Dict, Any, Tuple

# Resolve backend path and import query_kb
import sys
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from rag.rag_pipeline import query_kb, settings

BENCHMARK_PATH = os.path.join(backend_dir, "evaluation", "retrieval_benchmark.json")


def load_faiss_metadata() -> Dict[str, str]:
    """
    Loads faiss_metadata.json and returns a content-to-chunk_id map.
    This helps resolve the chunk ID of retrieved results by exact content matching.
    """
    project_root = os.path.dirname(backend_dir)
    metadata_file = os.path.join(project_root, settings.VECTOR_METADATA_PATH)
    if not os.path.exists(metadata_file):
        raise FileNotFoundError(f"FAISS metadata not found at: {metadata_file}")
        
    with open(metadata_file, "r", encoding="utf-8") as f:
        store = json.load(f)
        
    # Map normalized content -> chunk_id
    content_map = {}
    for chunk_id, data in store.items():
        clean_content = " ".join(data["content"].split())
        content_map[clean_content] = chunk_id
    return content_map


def dcg_at_k(relevances: List[int], k: int) -> float:
    """Calculates Discounted Cumulative Gain at K."""
    val = 0.0
    for i, rel in enumerate(relevances[:k]):
        val += rel / math.log2(i + 2)
    return val


def ndcg_at_k(relevances: List[int], expected_count: int, k: int) -> float:
    """Calculates Normalized Discounted Cumulative Gain at K."""
    dcg = dcg_at_k(relevances, k)
    # Ideal relevances: expected highly relevant (2) followed by partially relevant context (1)
    ideal_relevances = [2] * expected_count + [1] * max(0, k - expected_count)
    idcg = dcg_at_k(ideal_relevances[:k], k)
    if idcg <= 0.0:
        return 0.0
    return dcg / idcg



def evaluate_query(
    case: Dict[str, Any], 
    content_map: Dict[str, str], 
    k: int
) -> Tuple[Dict[str, Any], List[float], List[float]]:
    """
    Runs retrieval for a single benchmark query case at top_k = k.
    Returns:
        tuple: (query_result_dict, list_of_relevant_scores, list_of_irrelevant_scores)
    """
    query = case["query"]
    expected_chunks = case.get("expected_chunks", [])
    expected_sources = case.get("expected_sources", [])
    is_answerable = case["difficulty"] != "unanswerable"
    
    # Run retrieval
    retrieved_results = query_kb(query, top_k=k)
    
    # Resolve retrieved chunk IDs
    retrieved_chunk_ids = []
    retrieved_scores = []
    relevance_labels = []
    
    relevant_scores = []
    irrelevant_scores = []
    
    for r in retrieved_results:
        content = " ".join(r["content"].split())
        score = r["score"]
        source = r.get("metadata", {}).get("source", "")
        
        # Resolve chunk_id via exact text match
        chunk_id = content_map.get(content, "unknown")
        retrieved_chunk_ids.append(chunk_id)
        retrieved_scores.append(score)
        
        # Determine relevance label (2 = highly relevant, 1 = partially relevant context, 0 = irrelevant)
        if is_answerable and chunk_id in expected_chunks:
            relevance = 2
            relevant_scores.append(score)
        elif is_answerable and source in expected_sources:
            relevance = 1
            relevant_scores.append(score) # partially relevant is still a relevant hit
        else:
            relevance = 0
            irrelevant_scores.append(score)
            
        relevance_labels.append(relevance)
        
    # Calculate metrics
    hit = 0
    recall = 0.0
    mrr = 0.0
    ndcg = 0.0
    first_hit_rank = None
    
    if is_answerable and expected_chunks:
        # Check hits and rank
        for rank, chunk_id in enumerate(retrieved_chunk_ids):
            if chunk_id in expected_chunks:
                hit = 1
                first_hit_rank = rank + 1
                mrr = 1.0 / first_hit_rank
                break
                
        # Recall
        intersection = set(retrieved_chunk_ids).intersection(set(expected_chunks))
        recall = len(intersection) / len(expected_chunks)
        
        # nDCG
        ndcg = ndcg_at_k(relevance_labels, len(expected_chunks), k)
        
    return {
        "id": case["id"],
        "query": query,
        "is_answerable": is_answerable,
        "difficulty": case["difficulty"],
        "retrieved_chunk_ids": retrieved_chunk_ids,
        "retrieved_scores": retrieved_scores,
        "relevance_labels": relevance_labels,
        "hit": hit,
        "recall": recall,
        "mrr": mrr,
        "ndcg": ndcg,
        "first_hit_rank": first_hit_rank
    }, relevant_scores, irrelevant_scores


def run_evaluation(k_values: List[int] = [1, 3, 5]) -> Dict[str, Any]:
    print(f"Loading benchmark dataset from: {BENCHMARK_PATH}...")
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        benchmark = json.load(f)
        
    content_map = load_faiss_metadata()
    print(f"FAISS index loaded containing {len(content_map)} unique chunks.")
    
    results_by_k = {}
    score_analysis = {
        "relevant_scores": [],
        "irrelevant_scores": []
    }
    
    for k in k_values:
        print(f"\n--- Running Evaluation at K = {k} ---")
        query_evals = []
        
        ans_hit_count = 0
        ans_total_recall = 0.0
        ans_total_mrr = 0.0
        ans_total_ndcg = 0.0
        ans_count = 0
        unans_count = 0
        unans_false_positives = 0
        
        for case in benchmark:
            res, rel_s, irrel_s = evaluate_query(case, content_map, k)
            query_evals.append(res)
            
            # Record scores for distribution analysis (only at K=5 to get largest pool)
            if k == 5:
                score_analysis["relevant_scores"].extend(rel_s)
                score_analysis["irrelevant_scores"].extend(irrel_s)
                
            if res["is_answerable"]:
                ans_count += 1
                ans_hit_count += res["hit"]
                ans_total_recall += res["recall"]
                ans_total_mrr += res["mrr"]
                ans_total_ndcg += res["ndcg"]
            else:
                unans_count += 1
                # If any chunk was retrieved for unanswerable query, check score
                if res["retrieved_scores"]:
                    # A false positive is a retrieval returned above a loose threshold (e.g. 0.3)
                    max_score = max(res["retrieved_scores"])
                    if max_score > 0.35:
                        unans_false_positives += 1
                        
        hit_rate = ans_hit_count / ans_count if ans_count > 0 else 0.0
        recall_rate = ans_total_recall / ans_count if ans_count > 0 else 0.0
        mrr_rate = ans_total_mrr / ans_count if ans_count > 0 else 0.0
        ndcg_rate = ans_total_ndcg / ans_count if ans_count > 0 else 0.0
        false_positive_rate = unans_false_positives / unans_count if unans_count > 0 else 0.0
        
        print(f"Answerable Queries Evaluated : {ans_count}")
        print(f"Unanswerable Queries Evaluated: {unans_count}")
        print(f"Hit@{k}                        : {hit_rate:.4f}")
        print(f"Recall@{k}                     : {recall_rate:.4f}")
        print(f"MRR                           : {mrr_rate:.4f}")
        print(f"nDCG@{k}                      : {ndcg_rate:.4f}")
        print(f"Unanswerable False Positive   : {false_positive_rate:.4f} (at score > 0.35)")
        
        results_by_k[str(k)] = {
            "hit_at_k": hit_rate,
            "recall_at_k": recall_rate,
            "mrr": mrr_rate,
            "ndcg": ndcg_rate,
            "false_positive_rate": false_positive_rate,
            "cases": query_evals
        }
        
    # Score distribution stats
    rel_scores = score_analysis["relevant_scores"]
    irrel_scores = score_analysis["irrelevant_scores"]
    
    score_stats = {
        "relevant": {
            "count": len(rel_scores),
            "min": min(rel_scores) if rel_scores else 0.0,
            "max": max(rel_scores) if rel_scores else 0.0,
            "mean": statistics.mean(rel_scores) if rel_scores else 0.0,
            "median": statistics.median(rel_scores) if rel_scores else 0.0,
        },
        "irrelevant": {
            "count": len(irrel_scores),
            "min": min(irrel_scores) if irrel_scores else 0.0,
            "max": max(irrel_scores) if irrel_scores else 0.0,
            "mean": statistics.mean(irrel_scores) if irrel_scores else 0.0,
            "median": statistics.median(irrel_scores) if irrel_scores else 0.0,
        }
    }
    
    print("\n================ SCORE DISTRIBUTION ANALYSIS ================")
    print(f"Relevant Hits   -> Count: {score_stats['relevant']['count']}, Mean: {score_stats['relevant']['mean']:.4f}, Median: {score_stats['relevant']['median']:.4f}, Min: {score_stats['relevant']['min']:.4f}, Max: {score_stats['relevant']['max']:.4f}")
    print(f"Irrelevant Hits -> Count: {score_stats['irrelevant']['count']}, Mean: {score_stats['irrelevant']['mean']:.4f}, Median: {score_stats['irrelevant']['median']:.4f}, Min: {score_stats['irrelevant']['min']:.4f}, Max: {score_stats['irrelevant']['max']:.4f}")
    
    # Save report file
    report_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "index_type": "IndexFlatIP",
        "score_semantics": "Cosine Similarity (higher is better)",
        "results": results_by_k,
        "score_stats": score_stats
    }
    
    report_path = os.path.join(backend_dir, "knowledge_base", "evaluation_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
        
    print(f"\nSaved evaluation report JSON to: {report_path}")
    return report_data


if __name__ == "__main__":
    run_evaluation()
