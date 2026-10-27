import json
import time
import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.abspath("."))
from backend.app.services.ingestion_orchestrator import IngestionOrchestrator
from backend.app.core.config import settings

def main():
    orchestrator = IngestionOrchestrator()
    plans_to_ingest = [
        ("health_shield_basic.pdf", "HS-BASIC-001"),
        ("health_shield_gold.pdf", "HS-GOLD-001"),
        ("health_shield_premium.pdf", "HS-PREMIUM-001"),
        ("executive_employee_insurance_plan.pdf", "EMP-INS-001")
    ]

    results = []
    print("=== STARTING FULL END-TO-END INGESTION FOR ALL 4 PLANS ===")

    for fname, pid in plans_to_ingest:
        fpath = settings.SOURCE_PDFS_DIR / fname
        print(f"\n---> Ingesting: {fname} (Plan: {pid})")
        t0 = time.time()
        job = orchestrator.run_pipeline(
            pdf_path=fpath,
            original_filename=fname,
            selected_plan_id=pid
        )
        duration = round(time.time() - t0, 2)
        print(f"     Status: {job.status} in {duration}s")
        print(f"     Chunks stored: {job.records_stored} | Parents: {job.parent_chunks_count} | Children: {job.child_chunks_count}")
        results.append(job.to_dict())

    # Test Duplicate Ingestion (Health Shield Basic re-run)
    print("\n---> Testing Unchanged Duplicate Ingestion: health_shield_basic.pdf")
    dup_job = orchestrator.run_pipeline(
        pdf_path=settings.SOURCE_PDFS_DIR / "health_shield_basic.pdf",
        original_filename="health_shield_basic.pdf",
        selected_plan_id="HS-BASIC-001"
    )
    print(f"     Duplicate Test Status: {dup_job.status} (is_duplicate={dup_job.is_duplicate})")

    total_count = orchestrator.chroma_service.collection.count()
    print(f"\n=== ALL INGESTIONS COMPLETE ===")
    print(f"Total verified chunks in persistent ChromaDB collection 'insurance_knowledge': {total_count}")

    # Save summary stats
    out_file = settings.REPORTS_DIR / "ingestion_verification_report.json"
    summary_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "collection_name": settings.CHROMA_COLLECTION_NAME,
        "total_records_in_chroma": total_count,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "embedding_dimension": settings.EMBEDDING_DIMENSION,
        "duplicate_detection_verified": dup_job.status == "SKIPPED_DUPLICATE",
        "jobs": results
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Saved machine-readable JSON report to: {out_file}")

if __name__ == "__main__":
    main()
