from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from backend.app.api.deps import get_auth_user
from backend.app.services.auth_service import UserIdentity
from backend.app.services.eligibility_model_service import (
    eligibility_model_service,
    ApplicantEvaluationInput,
    EligibilityModelResult
)
from backend.app.db.sqlite_manager import sqlite_db
from backend.app.registry.plans import PLAN_REGISTRY

router = APIRouter(prefix="/eligibility", tags=["Eligibility Assessment & Underwriting"])

class PlanSelectionPayload(BaseModel):
    selected_plan_id: str = Field(..., description="Target plan ID (e.g. HS-GOLD-001)")
    assessment_id: Optional[str] = Field(None, description="Optional assessment ID; defaults to current active assessment")

class AgentContactPayload(BaseModel):
    assessment_id: Optional[str] = Field(None, description="Reference assessment ID")
    full_name: str = Field(..., min_length=2, max_length=100, description="Applicant full legal name")
    email: str = Field(..., min_length=5, max_length=100, description="Contact email address")
    phone: Optional[str] = Field(None, max_length=30, description="Contact phone number")
    preferred_contact_method: str = Field("EMAIL", description="'EMAIL' or 'PHONE'")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional context or questions")

@router.get("/health")
def get_model_health():
    """
    Readiness and availability check for the eligibility machine learning model package.
    """
    ready = eligibility_model_service.is_ready()
    return {
        "status": "ready" if ready else "unavailable",
        "model_loaded": ready,
        "metadata": eligibility_model_service.get_metadata() if ready else None
    }

@router.post("/assess")
def assess_applicant_eligibility(
    profile: ApplicantEvaluationInput,
    current_user: UserIdentity = Depends(get_auth_user)
):
    """
    Evaluates applicant data against the authentic Gradient Boosting model pipeline.
    Validates features, calculates BMI, performs ML prediction, and persists assessment.
    """
    try:
        result = eligibility_model_service.evaluate(profile, user_role=current_user.role)
        
        # Persist assessment in SQLite
        assessment_id = sqlite_db.save_eligibility_assessment(
            user_id=current_user.user_id,
            status=result.status,
            outcome=result.outcome,
            qualifying_plans=result.qualifying_plans,
            input_provenance=result.input_summary,
            model_id=result.model_id,
            model_version=result.model_version,
            confidence_score=result.probability_eligible,
            reason_codes=result.reason_codes,
            review_status=result.review_status
        )

        # Audit event
        sqlite_db.record_audit_event(
            action="eligibility_assessed",
            actor_id=current_user.user_id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            target_resource=assessment_id,
            outcome="SUCCESS" if result.outcome == "ELIGIBLE" else "REVIEW_REQUIRED",
            details={
                "outcome": result.outcome,
                "probability_eligible": result.probability_eligible,
                "bmi": result.bmi,
                "qualifying_plans": result.qualifying_plans
            }
        )

        return {
            "assessment_id": assessment_id,
            "outcome": result.outcome,
            "status": result.status,
            "probability_eligible": result.probability_eligible,
            "bmi": result.bmi,
            "qualifying_plans": result.qualifying_plans,
            "confidence_score": result.probability_eligible,
            "reason_codes": result.reason_codes,
            "review_status": result.review_status,
            "explanation": result.explanation,
            "input_summary": result.input_summary
        }
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid applicant features: {str(val_err)}"
        )
    except Exception as e:
        sqlite_db.record_audit_event(
            action="eligibility_assessment_failed",
            actor_id=current_user.user_id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            target_resource="eligibility_model",
            outcome="ERROR",
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Eligibility model evaluation failed: {str(e)}"
        )

@router.get("/me")
def get_my_current_assessment(current_user: UserIdentity = Depends(get_auth_user)):
    """
    Retrieves the authenticated user's current active eligibility assessment and active plan selection.
    """
    assessment = sqlite_db.get_current_assessment_for_user(current_user.user_id)
    active_selection = sqlite_db.get_active_plan_selection_for_user(current_user.user_id)

    if not assessment:
        return {
            "has_assessment": False,
            "assessment": None,
            "active_plan_selection": active_selection
        }

    return {
        "has_assessment": True,
        "assessment": assessment,
        "active_plan_selection": active_selection
    }

@router.post("/select-plan")
def select_plan_with_eligibility(
    payload: PlanSelectionPayload,
    current_user: UserIdentity = Depends(get_auth_user)
):
    """
    Records an active plan selection.
    Enforces that the user has an active ELIGIBLE assessment covering the selected plan.
    """
    assessment = sqlite_db.get_current_assessment_for_user(current_user.user_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Eligibility assessment required. Please complete eligibility check before selecting a plan."
        )

    if assessment["outcome"] != "ELIGIBLE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Current assessment outcome is '{assessment['outcome']}'. Plan selection is reserved for eligible applicants."
        )

    qualifying_plans = assessment.get("qualifying_plans", [])
    if payload.selected_plan_id not in qualifying_plans:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Plan '{payload.selected_plan_id}' is not in your qualified plans: {qualifying_plans}"
        )

    selection_id = sqlite_db.save_plan_selection(
        user_id=current_user.user_id,
        assessment_id=assessment["assessment_id"],
        selected_plan_id=payload.selected_plan_id
    )

    sqlite_db.record_audit_event(
        action="plan_selected",
        actor_id=current_user.user_id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        target_resource=payload.selected_plan_id,
        outcome="SUCCESS",
        details={"selection_id": selection_id, "assessment_id": assessment["assessment_id"]}
    )

    plan_info = PLAN_REGISTRY.get(payload.selected_plan_id)
    plan_name = plan_info.plan_name if plan_info else payload.selected_plan_id
    return {
        "selection_id": selection_id,
        "selected_plan_id": payload.selected_plan_id,
        "plan_name": plan_name,
        "status": "ACTIVE",
        "assessment_id": assessment["assessment_id"]
    }

@router.post("/agent-contact")
def request_agent_contact(
    payload: AgentContactPayload,
    current_user: UserIdentity = Depends(get_auth_user)
):
    """
    Submits a persisted assistance request to connect with a licensed human insurance agent.
    """
    try:
        request_id = sqlite_db.save_agent_contact_request(
            user_id=current_user.user_id,
            assessment_id=payload.assessment_id,
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            preferred_contact_method=payload.preferred_contact_method,
            notes=payload.notes
        )

        sqlite_db.record_audit_event(
            action="agent_assistance_requested",
            actor_id=current_user.user_id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            target_resource=request_id,
            outcome="SUCCESS",
            details={
                "request_id": request_id,
                "assessment_id": payload.assessment_id,
                "preferred_contact_method": payload.preferred_contact_method
            }
        )

        return {
            "request_id": request_id,
            "status": "PENDING",
            "message": "Your assistance request has been recorded. A licensed representative will contact you via your preferred method."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit agent assistance request: {str(e)}"
        )
