import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from backend.app.services.chroma_service import ChromaStorageService
from backend.app.core.config import settings

def run_deep_audit():
    print("=== STARTING DEEP READ-ONLY CHROMADB AUDIT ===")
    
    # 1. Initialize client and connect
    cs = ChromaStorageService()
    coll = cs.collection
    print(f"Collection: {coll.name}")
    print(f"Chroma Mode: {settings.CHROMA_MODE}")
    print(f"Cloud Host: {settings.CHROMA_CLOUD_HOST}")
    print(f"Total count reported by count(): {coll.count()}")
    
    # Fetch all records including embeddings and metadatas
    data = coll.get(include=["metadatas", "documents", "embeddings"])
    ids = data.get("ids", [])
    docs = data.get("documents", [])
    metas = data.get("metadatas", [])
    embeddings = data.get("embeddings", [])
    
    total_records = len(ids)
    print(f"Total records fetched: {total_records}")
    
    # Check ID uniqueness
    unique_ids = set(ids)
    is_unique_ids = len(ids) == len(unique_ids)
    print(f"Unique IDs: {len(unique_ids)} == {total_records} -> {is_unique_ids}")
    
    # Non-empty content
    empty_docs = [i for i, d in zip(ids, docs) if not d or not d.strip()]
    print(f"Empty documents count: {len(empty_docs)}")
    
    # Embedding verification
    embed_list = list(embeddings) if embeddings is not None else []
    embed_count = len(embed_list)
    dim_match = True
    all_finite = True
    dim_sizes = set()
    for emb in embed_list:
        if len(emb) != settings.EMBEDDING_DIMENSION:
            dim_match = False
        dim_sizes.add(len(emb))
        for v in emb:
            if not math.isfinite(v):
                all_finite = False
                break
    print(f"Embeddings count: {embed_count}, Dimensions found: {dim_sizes}, Expected: {settings.EMBEDDING_DIMENSION}")
    print(f"All dimensions match 384: {dim_match}")
    print(f"All embedding values finite: {all_finite}")
    
    # Read parent store
    parent_store = {}
    if settings.PARENT_STORE_PATH.exists():
        with open(settings.PARENT_STORE_PATH, "r", encoding="utf-8") as f:
            parent_store = json.load(f)
    print(f"Total records in parent_store.json: {len(parent_store)}")
    
    # Group by plan_id and source_document
    records_by_plan = defaultdict(list)
    records_by_doc = defaultdict(list)
    
    for record_id, doc, meta, emb in zip(ids, docs, metas, embeddings):
        pid = meta.get("plan_id", "UNKNOWN")
        sdoc = meta.get("source_document", "UNKNOWN")
        records_by_plan[pid].append((record_id, doc, meta, emb))
        records_by_doc[sdoc].append((record_id, doc, meta, emb))
        
    print("\n--- Breakdown by Plan ID ---")
    for pid, rlist in records_by_plan.items():
        print(f"  Plan ID: {pid} -> {len(rlist)} records")
        source_docs = Counter(m.get("source_document") for _, _, m, _ in rlist)
        print(f"    Source documents: {dict(source_docs)}")
        statuses = Counter(m.get("data_status") for _, _, m, _ in rlist)
        print(f"    Data statuses: {dict(statuses)}")
        
    print("\n--- Breakdown by Source Document ---")
    for sdoc, rlist in records_by_doc.items():
        print(f"  Source Document: {sdoc} -> {len(rlist)} records")
        pids = Counter(m.get("plan_id") for _, _, m, _ in rlist)
        print(f"    Plan IDs in metadata: {dict(pids)}")
        
    # Check required metadata fields and parent references
    required_meta_keys = [
        "plan_id", "source_document", "section_number", "section_title", 
        "source_page_start", "source_page_end", "content_type", "parent_section_id", "data_status"
    ]
    
    missing_meta_per_plan = defaultdict(int)
    broken_parents_per_plan = defaultdict(int)
    cross_contamination_per_plan = defaultdict(int)
    
    for record_id, doc, meta, emb in zip(ids, docs, metas, embeddings):
        pid = meta.get("plan_id")
        sdoc = meta.get("source_document")
        
        # Check required fields
        for k in required_meta_keys:
            if k not in meta or meta[k] is None or meta[k] == "":
                missing_meta_per_plan[pid] += 1
                
        # Check parent resolution
        parent_id = meta.get("parent_section_id")
        if not parent_id or parent_id not in parent_store:
            broken_parents_per_plan[pid] += 1
            
        # Check cross-contamination (e.g. source_document doesn't match plan_id)
        if pid == "HS-BASIC-001" and sdoc != "health_shield_basic.pdf":
            cross_contamination_per_plan[pid] += 1
        elif pid == "HS-GOLD-001" and sdoc != "health_shield_gold.pdf":
            cross_contamination_per_plan[pid] += 1
        elif pid == "HS-PREMIUM-001" and sdoc != "health_shield_premium.pdf":
            cross_contamination_per_plan[pid] += 1
        elif pid == "EMP-INS-001" and sdoc != "executive_employee_insurance_plan.pdf":
            cross_contamination_per_plan[pid] += 1

    print("\n--- Metadata & Integrity Checks ---")
    print(f"Missing metadata field instances by plan: {dict(missing_meta_per_plan)}")
    print(f"Broken parent references by plan: {dict(broken_parents_per_plan)}")
    print(f"Cross-plan contamination by plan: {dict(cross_contamination_per_plan)}")
    
    # Read-back test
    print("\n--- Read-Back Verification ---")
    readback_success = True
    for pid, rlist in records_by_plan.items():
        sample_ids = [r[0] for r in rlist[:5]]
        rb_res = coll.get(ids=sample_ids)
        rb_count = len(rb_res.get("ids", []))
        print(f"  Plan {pid}: requested {len(sample_ids)}, read back {rb_count}")
        if rb_count != len(sample_ids):
            readback_success = False
            
    print(f"Read-back overall success: {readback_success}")
    
    # Summary of findings
    expected_plans = ["HS-BASIC-001", "HS-GOLD-001", "HS-PREMIUM-001", "EMP-INS-001"]
    print("\n--- Audit Summary Against Expected Plans ---")
    for ep in expected_plans:
        actual_chunks = len(records_by_plan[ep])
        print(f"Plan {ep}:")
        print(f"  Persisted child chunks: {actual_chunks}")
        if actual_chunks == 0:
            print("  STATUS: FAIL - Zero records found in ChromaDB!")
        elif cross_contamination_per_plan[ep] > 0:
            print(f"  STATUS: FAIL - {cross_contamination_per_plan[ep]} records have mismatched source document!")
        elif broken_parents_per_plan[ep] > 0:
            print(f"  STATUS: FAIL - {broken_parents_per_plan[ep]} records reference non-existent parent records!")
        else:
            print("  STATUS: PASS")

if __name__ == "__main__":
    run_deep_audit()
