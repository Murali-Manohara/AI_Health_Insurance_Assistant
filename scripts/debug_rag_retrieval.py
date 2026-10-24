"""
Diagnostic Script for RAG Retrieval & Context Pipeline.
Captures Scope Resolution, Dense Search, BM25 Search, RRF Fusion, Parent Expansion,
and Final Formatted Context for 5 benchmark queries under Gold Plan (HS-GOLD-001).

Outputs report to: data/reports/rag_retrieval_debug.json
"""

import json
import math
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings
from backend.app.core.prompt import RAG_SYSTEM_PROMPT, format_rag_prompt
from backend.app.registry.plans import get_plan_by_id
from backend.app.services.auth_service import AuthorizationService
from backend.app.services.retrieval_service import HybridRetrievalService, RRF_K_DEFAULT
from backend.app.services.scope_resolver import ScopeResolver

QUERIES_TO_DEBUG = [
    "Hello",
    "What is the Daily Hospital Cash benefit, and what are its limits?",
    "What is the ICU limit per day and per year?",
    "What are the waiting periods for pre-existing conditions?",
    "What is the payout for Major Surgery Category 2?"
]

def preview_text(text: str, max_chars: int = 150) -> str:
    cleaned = " ".join(text.replace("\n", " ").split())
    if len(cleaned) > max_chars:
        return cleaned[:max_chars] + "..."
    return cleaned

def run_retrieval_diagnostics():
    print("=" * 80)
    print("RUNNING RAG RETRIEVAL DIAGNOSTICS (HS-GOLD-001 Scope)")
    print("=" * 80)

    retrieval_service = HybridRetrievalService()
    role = "customer"
    selected_plan_id = "HS-GOLD-001"
    top_k = 5
    rrf_k = RRF_K_DEFAULT

    debug_report = {
        "metadata": {
            "test_plan_id": selected_plan_id,
            "test_role": role,
            "top_k": top_k,
            "rrf_k": rrf_k,
            "parent_store_path": str(settings.PARENT_STORE_PATH),
            "chroma_collection": settings.CHROMA_COLLECTION_NAME,
            "embedding_dimension": settings.EMBEDDING_DIMENSION
        },
        "query_diagnostics": []
    }

    for query in QUERIES_TO_DEBUG:
        print(f"\n[QUERY]: '{query}'")

        # -------------------------------------------------------------
        # Stage A: Scope Resolution
        # -------------------------------------------------------------
        scope_res = ScopeResolver.resolve_scope(
            query=query,
            selected_plan_id=selected_plan_id,
            role=role,
            conversation_history=[]
        )

        stage_a = {
            "original_query": query,
            "resolved_query": query,
            "selected_plan_id": scope_res.selected_plan_id,
            "authorized_plans": scope_res.authorized_plans,
            "effective_scope": scope_res.effective_scope,
            "is_comparison": scope_res.is_comparison,
            "is_ambiguous": scope_res.is_ambiguous,
            "reason": scope_res.reason,
            "clarification_prompt": scope_res.clarification_prompt,
            "denied_plans": scope_res.denied_plans,
            "is_greeting": query.lower().strip() in ["hello", "hi", "hey", "greetings"]
        }
        print(f"  Stage A (Scope): effective_scope={scope_res.effective_scope}, reason={scope_res.reason}")

        # -------------------------------------------------------------
        # Stage B: Dense Retrieval
        # -------------------------------------------------------------
        dense_results = retrieval_service._dense_search(
            query=query,
            authorized_plans=scope_res.effective_scope,
            top_k=top_k * 2
        )

        stage_b = []
        for item in dense_results:
            meta = item.get("metadata", {})
            stage_b.append({
                "chunk_id": item.get("chunk_id"),
                "plan_id": item.get("plan_id"),
                "section_id": meta.get("parent_section_id") or meta.get("section_number"),
                "section_number": meta.get("section_number"),
                "section_title": meta.get("section_title"),
                "source_document": meta.get("source_document"),
                "pages": f"{meta.get('source_page_start', '')}-{meta.get('source_page_end', '')}",
                "dense_rank": item.get("dense_rank"),
                "raw_distance": item.get("dense_distance"),
                "distance_metric": "squared L2 or cosine distance (lower means closer)",
                "content_preview": preview_text(item.get("content", ""))
            })
        print(f"  Stage B (Dense): retrieved {len(stage_b)} candidates")

        # -------------------------------------------------------------
        # Stage C: BM25 Retrieval
        # -------------------------------------------------------------
        bm25_results = retrieval_service.bm25_service.search(
            query=query,
            authorized_plan_ids=scope_res.effective_scope,
            top_k=top_k * 2
        )

        stage_c = []
        for item in bm25_results:
            meta = item.get("metadata", {})
            stage_c.append({
                "chunk_id": item.get("chunk_id"),
                "plan_id": item.get("plan_id"),
                "section_id": meta.get("parent_section_id") or meta.get("section_number"),
                "section_number": meta.get("section_number"),
                "section_title": meta.get("section_title"),
                "bm25_rank": item.get("bm25_rank"),
                "bm25_score": item.get("bm25_score"),
                "content_preview": preview_text(item.get("content", ""))
            })
        print(f"  Stage C (BM25): retrieved {len(stage_c)} candidates")

        # -------------------------------------------------------------
        # Stage D: RRF Fusion
        # -------------------------------------------------------------
        fused_chunks = retrieval_service._reciprocal_rank_fusion(
            dense_results=dense_results,
            bm25_results=bm25_results,
            rrf_k=rrf_k,
            top_k=top_k
        )

        stage_d = []
        for rank, item in enumerate(fused_chunks, start=1):
            stage_d.append({
                "final_rank": rank,
                "chunk_id": item.get("chunk_id"),
                "plan_id": item.get("plan_id"),
                "dense_rank": item.get("dense_rank"),
                "bm25_rank": item.get("bm25_rank"),
                "rrf_score": round(item.get("rrf_score", 0.0), 6),
                "rrf_formula": f"1/({rrf_k}+{item.get('dense_rank')}) + 1/({rrf_k}+{item.get('bm25_rank')})"
            })
        print(f"  Stage D (RRF): fused into {len(stage_d)} chunks")

        # Post-fusion security filter
        sanitized_chunks = AuthorizationService.sanitize_retrieved_chunks(role, fused_chunks)

        # -------------------------------------------------------------
        # Stage E: Parent Section Expansion
        # -------------------------------------------------------------
        expanded_parents, contains_unverified = retrieval_service._expand_parents(
            sanitized_chunks, scope_res.effective_scope
        )

        stage_e = []
        seen_parent_ids = set()
        for c in sanitized_chunks:
            meta = c.get("metadata", {})
            pid = meta.get("parent_section_id")
            parent_record = retrieval_service.parent_store_data.get(pid, {}) if pid else {}
            
            was_already_included = pid in seen_parent_ids
            if pid:
                seen_parent_ids.add(pid)

            # Check if parent metadata matches chunk
            meta_match = (
                parent_record.get("plan_id") == meta.get("plan_id")
                and str(parent_record.get("section_number")) == str(meta.get("section_number"))
            )

            stage_e.append({
                "child_chunk_id": c.get("chunk_id"),
                "parent_section_id": pid,
                "parent_plan_id": parent_record.get("plan_id"),
                "section_title": parent_record.get("section_title") or meta.get("section_title"),
                "already_included": was_already_included,
                "metadata_match": meta_match,
                "parent_found_in_store": bool(parent_record),
                "parent_content_preview": preview_text(parent_record.get("full_content_markdown", "")),
                "parent_child_chunks": parent_record.get("child_chunk_ids", [])
            })

        print(f"  Stage E (Parent Expansion): expanded {len(expanded_parents)} unique parent sections")

        # -------------------------------------------------------------
        # Stage F: Final Context Sent to Gemini
        # -------------------------------------------------------------
        formatted_context = retrieval_service._build_context(sanitized_chunks, expanded_parents)
        plan_info = get_plan_by_id(selected_plan_id)
        selected_plan_name = plan_info.plan_name if plan_info else selected_plan_id
        full_gemini_prompt = format_rag_prompt(
            query=query,
            context_text=formatted_context,
            selected_plan_name=selected_plan_name,
            role=role,
            is_comparison=scope_res.is_comparison
        )

        stage_f = {
            "system_instruction": RAG_SYSTEM_PROMPT,
            "current_user_query": query,
            "relevant_conversation_history": [],
            "selected_plan": selected_plan_id,
            "selected_plan_name": selected_plan_name,
            "authorized_scope": scope_res.effective_scope,
            "contains_unverified_flag": contains_unverified,
            "retrieved_evidence_summary": [
                {
                    "source_id": f"Source {idx}",
                    "chunk_id": c.get("chunk_id"),
                    "plan_id": c.get("metadata", {}).get("plan_id"),
                    "section_number": c.get("metadata", {}).get("section_number"),
                    "section_title": c.get("metadata", {}).get("section_title"),
                    "pages": f"{c.get('metadata', {}).get('source_page_start')}-{c.get('metadata', {}).get('source_page_end')}",
                    "data_status": c.get("metadata", {}).get("data_status"),
                    "content_snippet": preview_text(c.get("content", ""))
                }
                for idx, c in enumerate(sanitized_chunks, start=1)
            ],
            "raw_formatted_context_preview": formatted_context[:800] + ("..." if len(formatted_context) > 800 else ""),
            "full_context_length_chars": len(formatted_context),
            "full_prompt_length_chars": len(full_gemini_prompt)
        }

        # Query Diagnostic Record
        query_record = {
            "query": query,
            "stage_a_scope_resolution": stage_a,
            "stage_b_dense_retrieval": stage_b,
            "stage_c_bm25_retrieval": stage_c,
            "stage_d_rrf_fusion": stage_d,
            "stage_e_parent_expansion": stage_e,
            "stage_f_final_gemini_context": stage_f
        }
        debug_report["query_diagnostics"].append(query_record)

    # Save to data/reports/rag_retrieval_debug.json
    out_path = PROJECT_ROOT / "data" / "reports" / "rag_retrieval_debug.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(debug_report, f, indent=2)

    print(f"\n[DONE] Diagnostic report saved to: {out_path}")
    return debug_report

if __name__ == "__main__":
    run_retrieval_diagnostics()
