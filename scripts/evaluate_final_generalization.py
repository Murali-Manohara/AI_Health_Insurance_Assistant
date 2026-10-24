import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.app.services.scope_resolver import ScopeResolver
from backend.app.services.retrieval_service import HybridRetrievalService
from backend.app.services.generation_service import AnswerGenerationService
from backend.app.services.conversation_service import ConversationManager
from backend.app.core.logging_config import logger

FINAL_GENERALIZATION_TESTS = [
    {
        "id": "FGEN-01",
        "category": "Numerical Calculation",
        "query": "Under Health Shield – Basic, what is the maximum hospital cash payment for an 8-day eligible hospital stay?",
        "selected_plan": "HS-BASIC-001",
        "role": "customer",
        "history": [],
        "expected_facts": ["16,000", "2,000", "8 days"],
        "expect_table": False
    },
    {
        "id": "FGEN-02",
        "category": "Plan Comparison",
        "query": "Compare the ICU daily allowance between Health Shield – Basic and Health Shield – Gold.",
        "selected_plan": "HS-BASIC-001",
        "role": "customer",
        "history": [],
        "expected_facts": ["4,000", "10,000"],
        "expect_table": True
    },
    {
        "id": "FGEN-03",
        "category": "Multi-Part Inquiry",
        "query": "For Health Shield – Gold: 1) What is the Category 1 surgery payout? 2) What is the overall surgery benefit limit? 3) Is day-care surgery covered?",
        "selected_plan": "HS-GOLD-001",
        "role": "customer",
        "history": [],
        "expected_facts": ["5,00,000", "25,00,000", "day-care"],
        "expect_table": False
    },
    {
        "id": "FGEN-04",
        "category": "Undefined Term & Uncertainty",
        "query": "What is the specific waiting period for cataract surgery under Health Shield – Basic?",
        "selected_plan": "HS-BASIC-001",
        "role": "customer",
        "history": [],
        "expected_facts": ["not finalized", "undefined", "unverified", "not specified"],
        "expect_table": False
    },
    {
        "id": "FGEN-05",
        "category": "Unfinalized Combination Rules",
        "query": "Are combination benefits for Major Surgery and Hospital Cash finalized under Health Shield – Premium?",
        "selected_plan": "HS-PREMIUM-001",
        "role": "customer",
        "history": [],
        "expected_facts": ["not verified", "not finalized", "unverified"],
        "expect_table": False
    },
    {
        "id": "FGEN-06",
        "category": "Claims Procedure Guidance",
        "query": "What procedure must an insured follow to submit hospital bills under Health Shield – Basic?",
        "selected_plan": "HS-BASIC-001",
        "role": "customer",
        "history": [],
        "expected_facts": ["1.", "2.", "claim"],
        "expect_table": False
    },
    {
        "id": "FGEN-07",
        "category": "General Knowledge (Vector Miss)",
        "query": "What is the difference between dense embeddings and sparse keyword search?",
        "selected_plan": "HS-BASIC-001",
        "role": "customer",
        "history": [],
        "expected_facts": ["dense", "sparse", "semantic", "keyword"],
        "expect_table": False
    },
    {
        "id": "FGEN-08",
        "category": "Platform Architecture Boundary",
        "query": "Does this insurance platform use LangChain or LlamaIndex for its retrieval pipeline?",
        "selected_plan": "HS-GOLD-001",
        "role": "customer",
        "history": [],
        "expected_facts": ["no", "fastapi", "chroma", "bm25"],
        "expect_table": False
    },
    {
        "id": "FGEN-09",
        "category": "Role Authorization Boundary",
        "query": "Compare the executive benefits in the Employee Plan with Health Shield – Gold.",
        "selected_plan": "HS-GOLD-001",
        "role": "customer",
        "history": [],
        "expected_facts": ["not authorized", "employee", "gold"],
        "expect_table": False
    },
    {
        "id": "FGEN-10",
        "category": "Conversational Follow-Up",
        "query": "Can you explain the hospitalization duration requirement for that?",
        "selected_plan": "HS-GOLD-001",
        "role": "customer",
        "history": [
            {
                "user_query": "What is the ICU benefit under Health Shield – Gold?",
                "assistant_answer": "Under Health Shield – Gold, the ICU daily benefit is **₹10,000 per day (illustrative)** for eligible intensive care treatment."
            }
        ],
        "expected_facts": ["24 hours", "exceeding"],
        "expect_table": False
    },
    {
        "id": "FGEN-11",
        "category": "Troubleshooting & Exclusion",
        "query": "Why would a claim for an elective cosmetic rhinoplasty be denied under Health Shield – Gold?",
        "selected_plan": "HS-GOLD-001",
        "role": "customer",
        "history": [],
        "expected_facts": ["exclusion", "cosmetic", "not covered", "elective"],
        "expect_table": False
    },
    {
        "id": "FGEN-12",
        "category": "Factual Transparency & Disclaimer",
        "query": "Is the ₹20,000 ICU benefit under Premium guaranteed by the IRDAI as a legal contract?",
        "selected_plan": "HS-PREMIUM-001",
        "role": "customer",
        "history": [],
        "expected_facts": ["not", "illustrative", "demonstration", "contract"],
        "expect_table": False
    }
]

def run_final_generalization_eval():
    scope_resolver = ScopeResolver()
    retrieval_service = HybridRetrievalService()
    generation_service = AnswerGenerationService()

    results = []
    print("=" * 80)
    print("RUNNING FINAL GENERALIZATION EVALUATION (12 FRESH UNSEEN QUERIES)")
    print("=" * 80)

    for idx, test in enumerate(FINAL_GENERALIZATION_TESTS, 1):
        tid = test["id"]
        category = test["category"]
        query = test["query"]
        plan = test["selected_plan"]
        role = test["role"]
        history = test.get("history", [])

        print(f"\n[{idx}/12] [{tid}] {category}\n     Query: '{query}'")

        # 1. Resolve Scope
        scope_res = scope_resolver.resolve_scope(
            query=query,
            selected_plan_id=plan,
            role=role,
            conversation_history=history
        )

        # 2. Retrieve & Generate
        if scope_res.is_greeting:
            answer_text = scope_res.greeting_message or "Hello! How can I help you today?"
            citations = []
            chunks_count = 0
        else:
            search_query = scope_res.resolved_query or query
            retrieval_res = retrieval_service.retrieve(
                query=search_query,
                role=role,
                effective_scope=scope_res.effective_scope,
                top_k=8 if scope_res.is_comparison else 7
            )
            chunks_count = len(retrieval_res.get("chunks", []))

            answer_res = generation_service.generate_answer(
                query=query,
                role=role,
                selected_plan_id=plan,
                retrieval_result=retrieval_res,
                is_comparison=scope_res.is_comparison,
                denied_plans=scope_res.denied_plans,
                conversation_history=history
            )
            answer_text = answer_res.answer_text
            citations = answer_res.citations

        ans_lower = answer_text.lower()
        first_line = answer_text.strip().split("\n")[0].lower()

        # Dimension 1: Directness (no throat-clearing)
        direct_pass = not any(
            tc in first_line
            for tc in ["based on the authorized", "based on your selected plan", "based on the policy evidence", "here is a detailed"]
        )

        # Dimension 2: Scan-friendly bold labels
        scan_pass = ("**" in answer_text) or scope_res.is_greeting

        # Dimension 3: Appropriate Structure (Table if requested)
        if test["expect_table"]:
            struct_pass = ("|" in answer_text and "---" in answer_text)
        else:
            struct_pass = True

        # Dimension 4: Factual Accuracy & Uncertainty
        expected_facts = test.get("expected_facts", [])
        matched = []
        for ef in expected_facts:
            ef_clean = ef.lower().replace(",", "").replace("₹", "")
            if ef.lower() in ans_lower or ef_clean in ans_lower.replace(",", "").replace("₹", ""):
                matched.append(ef)
        fact_cov = round((len(matched) / max(1, len(expected_facts))) * 100.0, 1)
        fact_pass = fact_cov >= 50.0

        # Dimension 5: No Duplicate Disclaimers
        no_dup_disc = not (ans_lower.count("note:") >= 1 and ans_lower.count("notice:") >= 1)

        # Dimension 6: Compact Citations
        bullet_count = answer_text.count("\n* ") + answer_text.count("\n- ")
        cit_tags = answer_text.count("[Health Shield") + answer_text.count("[Executive")
        compact_cit = (cit_tags <= max(2, bullet_count // 2 + 1)) or (bullet_count <= 2)

        checklist = [direct_pass, scan_pass, struct_pass, fact_pass, no_dup_disc, compact_cit]
        overall_score = round((sum(checklist) / len(checklist)) * 100.0, 1)
        passed = (overall_score >= 80.0) and fact_pass

        status_str = "PASS" if passed else "FAIL"
        print(f"     -> Result: {status_str} | Score: {overall_score}% | Direct: {direct_pass} | Scan: {scan_pass} | Struct: {struct_pass} | Facts: {fact_cov}% | Citations: {len(citations)}")

        results.append({
            "id": tid,
            "category": category,
            "query": query,
            "plan": plan,
            "overall_score": overall_score,
            "passed": passed,
            "metrics": {
                "directness": direct_pass,
                "scan_friendly": scan_pass,
                "appropriate_structure": struct_pass,
                "factual_uncertainty": fact_cov,
                "no_duplicate_disclaimer": no_dup_disc,
                "compact_citation": compact_cit
            },
            "answer_preview": answer_text[:250] + "..." if len(answer_text) > 250 else answer_text,
            "full_answer": answer_text
        })

    passed_count = sum(1 for r in results if r["passed"])
    avg_score = round(sum(r["overall_score"] for r in results) / len(results), 2)
    pass_rate = round((passed_count / len(results)) * 100.0, 1)

    print("\n" + "=" * 80)
    print(f"FINAL GENERALIZATION COMPLETE: {passed_count}/{len(results)} Passed ({pass_rate}%) | Avg Score: {avg_score}%")
    print("=" * 80)

    # Save reports
    report_data = {
        "metadata": {
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_tested": len(results),
            "total_passed": passed_count,
            "pass_rate_percentage": pass_rate,
            "average_score_percentage": avg_score,
            "llm_provider": generation_service.provider,
            "gemini_model": generation_service.gemini_model
        },
        "results": results
    }

    json_path = PROJECT_ROOT / "data" / "reports" / "final_generalization_evaluation.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"[SAVED] JSON report to: {json_path}")

    # Generate Markdown Report
    md_lines = [
        "# Final Generalization Evaluation Report",
        "",
        f"**Evaluation Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}  ",
        f"**LLM Model:** `{generation_service.gemini_model}` (Provider: `{generation_service.provider}`)  ",
        f"**Total Tested:** {len(results)}  ",
        f"**Overall Pass Rate:** **{pass_rate}%** ({passed_count}/{len(results)} Passed)  ",
        f"**Average Quality Score:** **{avg_score}%**  ",
        "",
        "---",
        "",
        "## 1. Summary of Results",
        "",
        "| ID | Category | Query Snippet | Score | Direct | Scan | Table | Facts | Status |",
        "|---|---|---|---:|:---:|:---:|:---:|:---:|:---:|"
    ]

    for r in results:
        direct = "✅" if r["metrics"]["directness"] else "❌"
        scan = "✅" if r["metrics"]["scan_friendly"] else "❌"
        tbl = "✅" if r["metrics"]["appropriate_structure"] else "❌"
        stat = "✅ PASS" if r["passed"] else "⚠️ ATTN"
        q_snip = r["query"][:35] + "..." if len(r["query"]) > 35 else r["query"]
        md_lines.append(
            f"| `{r['id']}` | **{r['category']}** | {q_snip} | **{r['overall_score']}%** | {direct} | {scan} | {tbl} | {r['metrics']['factual_uncertainty']}% | {stat} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "## 2. Detailed Transcripts",
        ""
    ])

    for r in results:
        md_lines.extend([
            f"### `{r['id']}`: {r['category']}",
            f"- **Query:** *\"{r['query']}\"*",
            f"- **Plan Context:** `{r['plan']}` | **Score:** **{r['overall_score']}%**",
            "```text",
            r["full_answer"],
            "```",
            ""
        ])

    md_path = PROJECT_ROOT / "data" / "reports" / "FINAL_GENERALIZATION_REPORT.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"[SAVED] Markdown report to: {md_path}")

if __name__ == "__main__":
    run_final_generalization_eval()
