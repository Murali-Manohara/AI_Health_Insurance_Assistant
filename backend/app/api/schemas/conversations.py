from pydantic import BaseModel, Field
from typing import Optional
from backend.app.services.generation_service import SourceCitation

class CreateConversationRequest(BaseModel):
    selected_plan_id: str = Field(..., description="Canonical Plan ID (e.g., HS-BASIC-001, HS-GOLD-001, HS-PREMIUM-001)")

class MessageRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="User question regarding insurance policy terms")

class MessageResponse(BaseModel):
    message_id: str
    role: str
    content: str
    timestamp: str
    citations: list[SourceCitation] = []
    effective_scope: list[str] = []
    is_comparison: bool = False
    is_clarification: bool = False
    contains_unverified_notice: bool = False

class ConversationResponse(BaseModel):
    conversation_id: str
    user_id: str
    role: str
    selected_plan_id: str
    created_at: str
    updated_at: str
    messages: list[MessageResponse] = []

class SendMessageResponse(BaseModel):
    message: MessageResponse
    scope_resolution: dict
    retrieval_diagnostics: dict
