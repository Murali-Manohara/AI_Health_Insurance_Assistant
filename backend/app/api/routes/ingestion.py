from fastapi import APIRouter, HTTPException, Depends
from typing import Any
from backend.app.api.deps import get_orchestrator
from backend.app.services.ingestion_orchestrator import IngestionOrchestrator
from backend.app.api.schemas.ingestion import IngestionJobResponse, HistoryItem

router = APIRouter(prefix="/ingestion", tags=["Ingestion Jobs & History"])

@router.get("/history", response_model=list[HistoryItem])
def get_ingestion_history(
    orchestrator: IngestionOrchestrator = Depends(get_orchestrator)
):
    """Retrieve persistent history of all past ingestion runs."""
    raw_history = orchestrator.get_history()
    return [HistoryItem(**item) for item in raw_history]

@router.get("/{job_id}", response_model=IngestionJobResponse)
def get_job_status(
    job_id: str,
    orchestrator: IngestionOrchestrator = Depends(get_orchestrator)
):
    """Retrieve detailed status and metrics for a specific ingestion job."""
    job = orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return IngestionJobResponse(**job.to_dict())

@router.get("/{job_id}/report")
def get_job_report(
    job_id: str,
    orchestrator: IngestionOrchestrator = Depends(get_orchestrator)
) -> dict[str, Any]:
    """Retrieve structured audit and loss-detection report for a completed run."""
    job = orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return {
        "job_id": job.job_id,
        "filename": job.filename,
        "plan_id": job.plan_id,
        "status": job.status,
        "duration_seconds": job.total_duration_sec,
        "stages_completed": job.stages_completed,
        "coverage_audit": job.coverage_report,
        "warnings": job.warnings,
        "errors": job.errors
    }
