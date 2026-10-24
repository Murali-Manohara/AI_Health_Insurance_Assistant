import pytest
from backend.app.services.ingestion_orchestrator import IngestionOrchestrator
from backend.app.core.config import settings

def test_full_pipeline_health_shield_basic():
    orchestrator = IngestionOrchestrator()
    pdf_path = settings.SOURCE_PDFS_DIR / "health_shield_basic.pdf"
    assert pdf_path.exists()

    job = orchestrator.run_pipeline(
        pdf_path=pdf_path,
        original_filename="health_shield_basic.pdf",
        selected_plan_id="HS-BASIC-001"
    )

    # If first run, SUCCESS. If re-run, SKIPPED_DUPLICATE or SUCCESS
    assert job.status in ["SUCCESS", "SKIPPED_DUPLICATE"]
    if job.status == "SUCCESS":
        assert job.records_stored > 0
        assert job.sections_detected >= 17
        assert len(job.stages_completed) == 9
        assert len(job.errors) == 0
