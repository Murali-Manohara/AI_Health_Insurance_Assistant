from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from backend.app.api.deps import get_orchestrator, get_admin_user
from backend.app.services.ingestion_orchestrator import IngestionOrchestrator
from backend.app.services.auth_service import UserIdentity
from backend.app.api.schemas.ingestion import IngestionJobResponse
from backend.app.utils.security import validate_pdf_bytes, save_to_staging
from backend.app.registry.plans import get_plan_by_id
from backend.app.core.logging_config import logger

router = APIRouter(prefix="", tags=["Upload & Ingestion"])

@router.post("/upload", response_model=IngestionJobResponse)
@router.post("/ingestion", response_model=IngestionJobResponse)
async def upload_and_ingest_pdf(
    file: UploadFile = File(...),
    plan_id: str = Form(...),
    current_user: UserIdentity = Depends(get_admin_user),
    orchestrator: IngestionOrchestrator = Depends(get_orchestrator)
):
    """
    Accepts PDF file upload and selected plan ID, executes the 9-stage ingestion pipeline,
    and returns comprehensive metrics and stage tracking.
    """
    logger.info(f"Received upload request for file '{file.filename}', selected plan_id: '{plan_id}'")
    
    # 1. Validate plan or category
    from backend.app.registry.plans import resolve_plan_from_selection
    plan_info = get_plan_by_id(plan_id) or resolve_plan_from_selection(plan_id)
    if not plan_info:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid selection '{plan_id}'. Must be 'Customer Insurance', 'Employee Insurance', or a valid plan ID."
        )

    # 2. Read bytes & security validation
    try:
        file_bytes = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=400, detail="Failed to read uploaded file stream.")

    validate_pdf_bytes(file_bytes, file.filename or "uploaded.pdf")

    # 3. Save to staging
    staging_path = save_to_staging(file_bytes, file.filename or "uploaded.pdf")

    # 4. Execute pipeline
    job = orchestrator.run_pipeline(
        pdf_path=staging_path,
        original_filename=file.filename or "uploaded.pdf",
        selected_plan_id=plan_id
    )

    if job.status == "FAILED":
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Ingestion failed at {job.current_stage}",
                "errors": job.errors,
                "warnings": job.warnings,
                "job_id": job.job_id
            }
        )

    return IngestionJobResponse(**job.to_dict())
