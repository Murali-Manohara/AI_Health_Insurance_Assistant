from fastapi import APIRouter, HTTPException, Depends, status
from backend.app.api.schemas.conversations import (
    CreateConversationRequest,
    ConversationResponse,
    MessageRequest,
    SendMessageResponse,
    MessageResponse
)
from backend.app.services.rag_orchestrator import RAGOrchestrator
from backend.app.services.auth_service import UserIdentity
from backend.app.api.deps import get_rag_orchestrator, get_auth_user
from backend.app.core.logging_config import logger

router = APIRouter(prefix="/conversations", tags=["Conversations & RAG Chat"])

@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    req: CreateConversationRequest,
    user: UserIdentity = Depends(get_auth_user),
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator)
):
    """
    Create a fresh plan-scoped conversation session.
    Fails closed with 403 Forbidden if plan is unauthorized for the user role.
    """
    try:
        session = orchestrator.conversation_manager.create_conversation(
            user_id=user.user_id,
            role=user.role,
            selected_plan_id=req.selected_plan_id
        )
        return ConversationResponse(**session.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    user: UserIdentity = Depends(get_auth_user),
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator)
):
    """Retrieve an existing authorized conversation session."""
    session = orchestrator.conversation_manager.get_conversation(conversation_id, user.user_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found or access denied."
        )
    return ConversationResponse(**session.model_dump())

@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_conversation_messages(
    conversation_id: str,
    user: UserIdentity = Depends(get_auth_user),
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator)
):
    """Retrieve turn history for an authorized conversation."""
    session = orchestrator.conversation_manager.get_conversation(conversation_id, user.user_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found or access denied."
        )
    return [MessageResponse(**m.model_dump()) for m in session.messages]

@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
def send_message(
    conversation_id: str,
    req: MessageRequest,
    user: UserIdentity = Depends(get_auth_user),
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator)
):
    """
    Process a user message:
    1. Resolve plan scope (selected plan by default, explicit comparison if authorized)
    2. Hybrid retrieve authorized evidence
    3. Generate grounded answer with citations
    4. Persist turn state and return
    """
    try:
        result = orchestrator.process_query(
            conversation_id=conversation_id,
            user=user,
            query=req.query
        )
        return SendMessageResponse(
            message=MessageResponse(**result["message"]),
            scope_resolution=result["scope_resolution"],
            retrieval_diagnostics=result["retrieval_diagnostics"]
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process message: {str(e)}")
