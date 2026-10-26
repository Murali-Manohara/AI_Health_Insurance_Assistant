from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.services.auth_service import UserIdentity
from backend.app.api.deps import get_employee_user, get_rag_orchestrator
from backend.app.services.rag_orchestrator import RAGOrchestrator
from backend.app.services.claim_predictor_service import claim_predictor_service
from backend.app.api.schemas.claim_predictor import (
    ClaimPredictionInput,
    ClaimPredictionResponse
)
from backend.app.core.logging_config import logger

router = APIRouter(prefix="/claim-predictor", tags=["Claim Predictor"])

@router.post("/predict", response_model=ClaimPredictionResponse, status_code=status.HTTP_200_OK)
def predict_claim_payout(
    req: ClaimPredictionInput,
    user: UserIdentity = Depends(get_employee_user),
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator)
):
    """
    Employee-only endpoint to generate insurance claim payout predictions
    using the trained regression model from claim_predictor_package.
    Optionally pipes the prediction and validated input parameters to the active
    RAG LLM conversation to generate a grounded conversational explanation.
    """
    logger.info(f"User '{user.user_id}' (role='{user.role}') requested claim prediction for plan '{req.plan}', claim_type='{req.claim_type}'")

    # 1. Run model prediction
    prediction_result = claim_predictor_service.predict(req)

    message = None
    user_message = None
    retrieval_diagnostics = None

    # 2. If an active conversation ID is provided, pipe prediction to RAG LLM
    if req.conversation_id:
        try:
            rag_output = orchestrator.process_claim_prediction(
                conversation_id=req.conversation_id,
                user=user,
                prediction_result=prediction_result
            )
            message = rag_output.get("message")
            user_message = rag_output.get("user_message")
            retrieval_diagnostics = rag_output.get("retrieval_diagnostics")
        except ValueError as ve:
            logger.warning(f"Failed to attach claim prediction to conversation '{req.conversation_id}': {ve}")
            # Keep prediction result even if conversation wasn't found
        except Exception as e:
            logger.error(f"Error during RAG explanation generation for claim prediction: {e}", exc_info=True)
            # Retain prediction result, do not crash

    return ClaimPredictionResponse(
        request_id=prediction_result["request_id"],
        prediction=prediction_result["prediction"],
        formatted_prediction=prediction_result["formatted_prediction"],
        output_units=prediction_result["output_units"],
        validated_inputs=prediction_result["validated_inputs"],
        message=message,
        assistant_message=message,
        user_message=user_message,
        retrieval_diagnostics=retrieval_diagnostics
    )
