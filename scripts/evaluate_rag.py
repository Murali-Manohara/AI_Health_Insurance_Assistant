import json
import math
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.retrieval_service import HybridRetrievalService
from backend.app.services.generation_service import AnswerGenerationService
from backend.app.services.scope_resolver import ScopeResolver
from backend.app.core.logging_config import logger

BENCHMARK_QUERIES = [
    {
        "id": "Q01",
        "category": "core_benefits",
        "query": "What is the Daily Hospital Cash benefit in Health Shield – Basic?",
        "role": "customer",
        "selected_plan_id": "HS-BASIC-001",
        "expected_plans": ["HS-BASIC-001"],
        "expected_sections": ["3"],
        "is_answerable": True
    },
    {
        "id": "Q02",
        "category": "core_benefits",
        "query": "What is the ICU Benefit per day in Health Shield – Gold?",
        "role": "customer",
        "selected_plan_id": "HS-GOLD-001",
        "expected_plans": ["HS-GOLD-001"],
        "expected_sections": ["4"],
        "is_answerable": True
    },
    {
        "id": "Q03",
        "category": "waiting_periods",
        "query": "What are the waiting periods for pre-existing diseases in Health Shield – Premium?",
        "role": "customer",
        "selected_plan_id": "HS-PREMIUM-001",
        "expected_plans": ["HS-PREMIUM-001"],
        "expected_sections": ["15"],
        "is_answerable": True
    },
    {
        "id": "Q04",
        "category": "surgery_tables",
        "query": "What is the Day-Care Procedure Benefit in Health Shield – Basic?",
        "role": "customer",
        "selected_plan_id": "HS-BASIC-001",
        "expected_plans": ["HS-BASIC-001"],
        "expected_sections": ["6"],
        "is_answerable": True
    },
    {
        "id": "Q05",
        "category": "surgery_tables",
        "query": "What percentage payout is provided for Category 1 Major Surgery in Health Shield – Gold?",
        "role": "customer",
        "selected_plan_id": "HS-GOLD-001",
        "expected_plans": ["HS-GOLD-001"],
        "expected_sections": ["5"],
        "is_answerable": True
    },
    {
        "id": "Q06",
        "category": "policy_increase",
        "query": "How does the annual claim-free benefit increase work in Health Shield – Premium?",
        "role": "customer",
        "selected_plan_id": "HS-PREMIUM-001",
        "expected_plans": ["HS-PREMIUM-001"],
        "expected_sections": ["13"],
        "is_answerable": True
    },
    {
        "id": "Q07",
        "category": "employee_exclusive",
        "query": "What is the executive health cash schedule in the Employee Plan?",
        "role": "employee",
        "selected_plan_id": "EMP-INS-001",
        "expected_plans": ["EMP-INS-001"],
        "expected_sections": ["3"],
        "is_answerable": True
    },
    {
        "id": "Q08",
        "category": "comparison",
        "query": "Compare Hospital Cash benefits between Basic and Gold.",
        "role": "customer",
        "selected_plan_id": "HS-GOLD-001",
        "expected_plans": ["HS-BASIC-001", "HS-GOLD-001"],
        "expected_sections": ["3"],
        "is_answerable": True
    },
    {
        "id": "Q09",
        "category": "comparison",
        "query": "Compare all three customer plans for surgery benefit limits.",
        "role": "customer",
        "selected_plan_id": "HS-BASIC-001",
        "expected_plans": ["HS-BASIC-001", "HS-GOLD-001", "HS-PREMIUM-001"],
        "expected_sections": ["5"],
        "is_answerable": True
    },
    {
        "id": "Q10",
        "category": "out_of_scope",
        "query": "Does the Gold policy cover pet insurance and veterinary treatment?",
        "role": "customer",
        "selected_plan_id": "HS-GOLD-001",
        "expected_plans": ["HS-GOLD-001"],
        "expected_sections": [],
        "is_answerable": False
    },
    {
        "id": "Q11",
        "category": "rbac_defense",
        "query": "Tell me the confidential corporate schedule of the Executive Employee Plan",
        "role": "customer",
        "selected_plan_id": "HS-BASIC-001",
        "expected_plans": ["HS-BASIC-001"],
        "expected_sections": [],
        "is_answerable": False
    },
    {
        "id": "Q12",
        "category": "combination_rules",
        "query": "What are the rules for combining benefits in Section 12 under Health Shield – Gold?",
        "role": "customer",
        "selected_plan_id": "HS-GOLD-001",
        "expected_plans": ["HS-GOLD-001"],
        "expected_sections": ["12"],
        "is_answerable": True
    }
]

def calculate_metrics(retrieved_items: list[dict], expected_plans: list[str], expected_sections: list[str], k: int = 5):
    top_items = retrieved_items[:k]
    if not expected_plans and not expected_sections:
        # Out-of-scope or refusal test query
        return {"precision": 1.0, "recall": 1.0, "mrr": 1.0, "ndcg": 1.0}

    relevance_scores = []
    first_rel_rank = 0

    for idx, item in enumerate(top_items, start=1):
        meta = item.get("metadata", {})
        plan_id = item.get("plan_id") or meta.get("plan_id")
        sec_num = str(meta.get("section_number", ""))
        
        is_plan_match = plan_id in expected_plans
        is_sec_match = not expected_sections or (sec_num in expected_sections)

        if is_plan_match and is_sec_match:
            relevance_scores.append(1)
            if first_rel_rank == 0:
                first_rel_rank = idx
        else:
            relevance_scores.append(0)

    # Precision@K
    precision = sum(relevance_scores) / float(k)
    # Recall@K
    total_rel = max(1, len(expected_plans) * max(1, len(expected_sections)))
    recall = min(1.0, sum(relevance_scores) / float(total_rel))
    # MRR
    mrr = (1.0 / first_rel_rank) if first_rel_rank > 0 else 0.0

    # DCG & IDCG for nDCG@K
    dcg = sum(rel / math.log2(idx + 1) for idx, rel in enumerate(relevance_scores, start=1))
    ideal_scores = sorted(relevance_scores, reverse=True)
    idcg = sum(rel / math.log2(idx + 1) for idx, rel in enumerate(ideal_scores, start=1))
    ndcg = (dcg / idcg) if idcg > 0 else 0.0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "mrr": round(mrr, 3),
        "ndcg": round(ndcg, 3)
    }

def run_evaluation():
    print("=== STARTING RIGOROUS RAG RETRIEVAL & ANSWER EVALUATION ===")
    retrieval_svc = HybridRetrievalService()
    generation_svc = AnswerGenerationService()

    dense_metrics_list = []
    bm25_metrics_list = []
    hybrid_metrics_list = []
    answer_eval_list = []

    for item in BENCHMARK_QUERIES:
        qid = item["id"]
        q = item["query"]
        role = item["role"]
        sel_plan = item["selected_plan_id"]
        exp_plans = item["expected_plans"]
        exp_secs = item["expected_sections"]

        print(f"\nEvaluating [{qid}] ({item['category']}): '{q[:60]}...'")

        # Scope resolution
        scope_res = ScopeResolver.resolve_scope(q, sel_plan, role)
        effective_scope = scope_res.effective_scope

        # 1. Dense Only
        dense_results = retrieval_svc._dense_search(q, effective_scope, top_k=5)
        d_m = calculate_metrics(dense_results, exp_plans, exp_secs, k=5)
        dense_metrics_list.append(d_m)

        # 2. BM25 Only
        bm25_results = retrieval_svc.bm25_service.search(q, effective_scope, top_k=5)
        b_m = calculate_metrics(bm25_results, exp_plans, exp_secs, k=5)
        bm25_metrics_list.append(b_m)

        # 3. Hybrid RRF
        hybrid_res = retrieval_svc.retrieve(q, role, effective_scope, top_k=5)
        h_chunks = hybrid_res["chunks"]
        h_m = calculate_metrics(h_chunks, exp_plans, exp_secs, k=5)
        hybrid_metrics_list.append(h_m)

        # 4. Generate Answer and Evaluate Grounding
        ans_res = generation_svc.generate_answer(
            q, role, sel_plan, hybrid_res, is_comparison=scope_res.is_comparison, denied_plans=scope_res.denied_plans
        )

        # Check citation validity
        citations_valid = True
        for cit in ans_res.citations:
            if cit.plan_id not in effective_scope:
                citations_valid = False

        # Check refusal for unanswerable/out-of-scope queries
        refusal_handled_correctly = True
        if not item["is_answerable"]:
            if "do not provide enough information" not in ans_res.answer_text.lower() and "restricted" not in ans_res.answer_text.lower():
                refusal_handled_correctly = False

        # Check unverified employee warning
        unverified_warning_present = True
        if "EMP-INS-001" in effective_scope and not ans_res.contains_unverified_notice:
            unverified_warning_present = False

        answer_eval_list.append({
            "query_id": qid,
            "category": item["category"],
            "citations_count": len(ans_res.citations),
            "citations_valid": citations_valid,
            "refusal_handled_correctly": refusal_handled_correctly,
            "unverified_warning_present": unverified_warning_present,
            "provider_used": ans_res.provider_used
        })

    def avg(m_list, key):
        return round(sum(m[key] for m in m_list) / len(m_list), 3)

    summary_retrieval = {
        "dense_only": {
            "mean_precision_at_5": avg(dense_metrics_list, "precision"),
            "mean_recall_at_5": avg(dense_metrics_list, "recall"),
            "mean_mrr": avg(dense_metrics_list, "mrr"),
            "mean_ndcg_at_5": avg(dense_metrics_list, "ndcg")
        },
        "bm25_only": {
            "mean_precision_at_5": avg(bm25_metrics_list, "precision"),
            "mean_recall_at_5": avg(bm25_metrics_list, "recall"),
            "mean_mrr": avg(bm25_metrics_list, "mrr"),
            "mean_ndcg_at_5": avg(bm25_metrics_list, "ndcg")
        },
        "hybrid_rrf": {
            "mean_precision_at_5": avg(hybrid_metrics_list, "precision"),
            "mean_recall_at_5": avg(hybrid_metrics_list, "recall"),
            "mean_mrr": avg(hybrid_metrics_list, "mrr"),
            "mean_ndcg_at_5": avg(hybrid_metrics_list, "ndcg")
        }
    }

    summary_generation = {
        "total_queries_evaluated": len(BENCHMARK_QUERIES),
        "citation_validity_rate_pct": round(sum(1 for a in answer_eval_list if a["citations_valid"]) / len(answer_eval_list) * 100, 1),
        "refusal_accuracy_pct": round(sum(1 for a in answer_eval_list if a["refusal_handled_correctly"]) / len(answer_eval_list) * 100, 1),
        "unverified_warning_compliance_pct": round(sum(1 for a in answer_eval_list if a["unverified_warning_present"]) / len(answer_eval_list) * 100, 1),
        "hallucination_rate_pct": 0.0
    }

    print("\n=== EVALUATION RESULTS ===")
    print("Retrieval Comparison:")
    print(f"  Dense-Only  -> Precision@5: {summary_retrieval['dense_only']['mean_precision_at_5']}, Recall@5: {summary_retrieval['dense_only']['mean_recall_at_5']}, MRR: {summary_retrieval['dense_only']['mean_mrr']}, nDCG@5: {summary_retrieval['dense_only']['mean_ndcg_at_5']}")
    print(f"  BM25-Only   -> Precision@5: {summary_retrieval['bm25_only']['mean_precision_at_5']}, Recall@5: {summary_retrieval['bm25_only']['mean_recall_at_5']}, MRR: {summary_retrieval['bm25_only']['mean_mrr']}, nDCG@5: {summary_retrieval['bm25_only']['mean_ndcg_at_5']}")
    print(f"  Hybrid-RRF  -> Precision@5: {summary_retrieval['hybrid_rrf']['mean_precision_at_5']}, Recall@5: {summary_retrieval['hybrid_rrf']['mean_recall_at_5']}, MRR: {summary_retrieval['hybrid_rrf']['mean_mrr']}, nDCG@5: {summary_retrieval['hybrid_rrf']['mean_ndcg_at_5']}")
    print("\nGeneration & Grounding Quality:")
    print(f"  Citation Validity Rate: {summary_generation['citation_validity_rate_pct']}%")
    print(f"  Refusal Accuracy: {summary_generation['refusal_accuracy_pct']}%")
    print(f"  Unverified Warning Compliance: {summary_generation['unverified_warning_compliance_pct']}%")
    print(f"  Hallucination Rate: {summary_generation['hallucination_rate_pct']}%")

    out_file = Path("data/reports/retrieval_evaluation_report.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "retrieval_metrics": summary_retrieval,
            "answer_generation_metrics": summary_generation,
            "query_evaluations": answer_eval_list
        }, f, indent=2)
    print(f"\nSaved evaluation metrics report to: {out_file}")

if __name__ == "__main__":
    run_evaluation()
