import time
from typing import Optional
from backend.app.services.auth_service import UserIdentity, AuthorizationService
from backend.app.services.scope_resolver import ScopeResolver, ScopeResolutionResult
from backend.app.services.retrieval_service import HybridRetrievalService
from backend.app.services.generation_service import AnswerGenerationService, GroundedAnswerResult
from backend.app.services.conversation_service import ConversationManager, ConversationSession, ChatMessage
from backend.app.core.logging_config import logger

class RAGOrchestrator:
    """
    Coordinates end-to-end plan-scoped RAG flow:
    Authentication -> Scope Resolution -> Hybrid Retrieval -> Answer Generation -> Session Persistence
    """

    def __init__(
        self,
        retrieval_service: Optional[HybridRetrievalService] = None,
        generation_service: Optional[AnswerGenerationService] = None,
        conversation_manager: Optional[ConversationManager] = None
    ):
        self.retrieval_service = retrieval_service or HybridRetrievalService()
        self.generation_service = generation_service or AnswerGenerationService()
        self.conversation_manager = conversation_manager or ConversationManager()

    def process_query(
        self,
        conversation_id: str,
        user: UserIdentity,
        query: str
    ) -> dict:
        session = self.conversation_manager.get_conversation(conversation_id, user.user_id)
        if not session:
            raise ValueError(f"Conversation session '{conversation_id}' not found for user '{user.user_id}'.")

        logger.info(f"[{conversation_id}] Processing query for role='{user.role}', plan='{session.selected_plan_id}': '{query[:80]}'")

        # 1. Resolve effective retrieval scope and comparisons
        scope_result = ScopeResolver.resolve_scope(
            query=query,
            selected_plan_id=session.selected_plan_id,
            role=user.role,
            conversation_history=[m.model_dump() for m in session.messages]
        )

        # 1.5 Handle Greeting queries directly without unnecessary retrieval or disclaimers
        if scope_result.is_greeting:
            assistant_msg = self.conversation_manager.add_turn(
                conversation_id=conversation_id,
                user_id=user.user_id,
                user_query=query,
                assistant_answer=scope_result.greeting_message or "Hello! How can I help you today?",
                citations=[],
                effective_scope=scope_result.effective_scope,
                is_comparison=False,
                is_clarification=False,
                contains_unverified=False
            )
            return {
                "message": assistant_msg.model_dump(),
                "scope_resolution": scope_result.model_dump(),
                "retrieval_diagnostics": {"greeting": True}
            }

        # 2. Check for Ambiguous query requiring clarification
        if scope_result.is_ambiguous:
            assistant_msg = self.conversation_manager.add_turn(
                conversation_id=conversation_id,
                user_id=user.user_id,
                user_query=query,
                assistant_answer=scope_result.clarification_prompt or "Please clarify which plans you want to compare.",
                citations=[],
                effective_scope=scope_result.effective_scope,
                is_comparison=True,
                is_clarification=True,
                contains_unverified=False
            )
            return {
                "message": assistant_msg.model_dump(),
                "scope_resolution": scope_result.model_dump(),
                "retrieval_diagnostics": {}
            }

        # 3. Execute Hybrid Retrieval with contextualized resolved query
        t_start = time.time()
        search_query = scope_result.resolved_query or query
        t_ret_start = time.time()
        retrieval_res = self.retrieval_service.retrieve(
            query=search_query,
            role=user.role,
            effective_scope=scope_result.effective_scope,
            top_k=8 if scope_result.is_comparison else 7
        )
        t_retrieval_ms = (time.time() - t_ret_start) * 1000.0

        # 4. Generate Grounded Answer with Citations
        history_list = [m.model_dump() for m in session.messages]
        t_gen_start = time.time()
        answer_res = self.generation_service.generate_answer(
            query=query,
            role=user.role,
            selected_plan_id=session.selected_plan_id,
            retrieval_result=retrieval_res,
            is_comparison=scope_result.is_comparison,
            denied_plans=scope_result.denied_plans,
            conversation_history=history_list
        )
        t_generation_ms = (time.time() - t_gen_start) * 1000.0
        t_total_ms = (time.time() - t_start) * 1000.0

        # 5. Persist turn to conversation session
        assistant_msg = self.conversation_manager.add_turn(
            conversation_id=conversation_id,
            user_id=user.user_id,
            user_query=query,
            assistant_answer=answer_res.answer_text,
            citations=answer_res.citations,
            effective_scope=scope_result.effective_scope,
            is_comparison=scope_result.is_comparison,
            is_clarification=False,
            contains_unverified=answer_res.contains_unverified_notice
        )

        # 6. Record telemetry safely into persistent database
        try:
            from backend.app.db.sqlite_manager import sqlite_db
            retrieved_chunks = retrieval_res.get("chunks", [])
            status_val = "SUCCESS" if answer_res.citations or retrieved_chunks else "NO_EVIDENCE"
            sqlite_db.record_rag_metric(
                request_id=f"req_{conversation_id[:8]}",
                user_id=user.user_id,
                role=user.role,
                plan_id=session.selected_plan_id,
                latency_retrieval_ms=t_retrieval_ms,
                latency_generation_ms=t_generation_ms,
                latency_total_ms=t_total_ms,
                retrieved_chunks_count=len(retrieved_chunks),
                citations_count=len(answer_res.citations),
                is_comparison=scope_result.is_comparison,
                status=status_val
            )
        except Exception as e:
            logger.warning(f"Telemetry recording skipped: {e}")

        return {
            "message": assistant_msg.model_dump(),
            "scope_resolution": scope_result.model_dump(),
            "retrieval_diagnostics": retrieval_res.get("diagnostics", {})
        }
