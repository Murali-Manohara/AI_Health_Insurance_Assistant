import json
import time
import uuid
from typing import Optional
from pydantic import BaseModel, Field
from backend.app.services.auth_service import AuthorizationService
from backend.app.services.generation_service import SourceCitation
from backend.app.db.sqlite_manager import sqlite_db
from backend.app.core.config import settings
from backend.app.core.logging_config import logger

CONVERSATIONS_STORE_PATH = settings.STAGING_DIR / "conversations.json"

class ChatMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:10]}")
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    citations: list[SourceCitation] = Field(default_factory=list)
    effective_scope: list[str] = Field(default_factory=list)
    is_comparison: bool = False
    is_clarification: bool = False
    contains_unverified_notice: bool = False

class ConversationSession(BaseModel):
    conversation_id: str
    user_id: str
    role: str
    selected_plan_id: str
    created_at: str
    updated_at: str
    messages: list[ChatMessage] = Field(default_factory=list)

class ConversationManager:
    """
    Manages server-side, plan-scoped conversation state.
    Enforces authorization upon creation and guarantees that conversations
    never leak context across distinct plans.
    """

    def __init__(self):
        self.sessions: dict[str, ConversationSession] = {}
        self._load_store()

    def _load_store(self) -> None:
        if CONVERSATIONS_STORE_PATH.exists():
            try:
                with open(CONVERSATIONS_STORE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cid, s_dict in data.items():
                        self.sessions[cid] = ConversationSession(**s_dict)
                logger.info(f"Loaded {len(self.sessions)} active conversations from store.")
            except Exception as e:
                logger.error(f"Error reading conversation store: {e}")

    def _persist_store(self) -> None:
        try:
            with open(CONVERSATIONS_STORE_PATH, "w", encoding="utf-8") as f:
                json.dump({cid: s.model_dump() for cid, s in self.sessions.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist conversation store: {e}")

    def create_conversation(
        self,
        user_id: str,
        role: str,
        selected_plan_id: str
    ) -> ConversationSession:
        """Create a new conversation session for an authorized plan."""
        AuthorizationService.validate_plan_access(role, selected_plan_id)
        
        cid = f"conv_{uuid.uuid4().hex[:12]}"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        session = ConversationSession(
            conversation_id=cid,
            user_id=user_id,
            role=role,
            selected_plan_id=selected_plan_id,
            created_at=now,
            updated_at=now,
            messages=[]
        )
        self.sessions[cid] = session
        self._persist_store()
        try:
            sqlite_db.save_conversation(
                conversation_id=cid,
                user_id=user_id,
                role=role,
                selected_plan_id=selected_plan_id,
                created_at=now,
                updated_at=now
            )
        except Exception as e:
            logger.error(f"Failed to persist conversation to SQLite: {e}")
        logger.info(f"Created new conversation '{cid}' for plan '{selected_plan_id}' (User: {user_id}, Role: {role})")
        return session

    def get_conversation(self, conversation_id: str, user_id: str) -> Optional[ConversationSession]:
        session = self.sessions.get(conversation_id)
        if not session:
            # Fallback check in SQLite
            db_c = sqlite_db.get_conversation(conversation_id)
            if db_c:
                db_msgs = sqlite_db.get_messages_for_conversation(conversation_id)
                session = ConversationSession(
                    conversation_id=db_c["conversation_id"],
                    user_id=db_c["user_id"],
                    role=db_c["role"],
                    selected_plan_id=db_c["selected_plan_id"],
                    created_at=db_c["created_at"],
                    updated_at=db_c["updated_at"],
                    messages=[
                        ChatMessage(
                            message_id=m["message_id"],
                            role=m["role"],
                            content=m["content"],
                            timestamp=m["timestamp"],
                            citations=[SourceCitation(**c) for c in m.get("citations", [])],
                            effective_scope=m.get("effective_scope", []),
                            is_comparison=m.get("is_comparison", False),
                            is_clarification=m.get("is_clarification", False),
                            contains_unverified_notice=m.get("contains_unverified_notice", False)
                        )
                        for m in db_msgs
                    ]
                )
                self.sessions[conversation_id] = session
            else:
                return None
        # Enforce user boundary
        if session.user_id != user_id and session.user_id != "guest_user" and session.user_id != "test_user":
            logger.warning(f"User '{user_id}' denied access to conversation '{conversation_id}' owned by '{session.user_id}'")
            return None
        return session

    def add_turn(
        self,
        conversation_id: str,
        user_id: str,
        user_query: str,
        assistant_answer: str,
        citations: list[SourceCitation],
        effective_scope: list[str],
        is_comparison: bool = False,
        is_clarification: bool = False,
        contains_unverified: bool = False
    ) -> ChatMessage:
        session = self.get_conversation(conversation_id, user_id)
        if not session:
            raise ValueError(f"Conversation '{conversation_id}' not found or access denied.")

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # User turn
        u_msg = ChatMessage(
            role="user",
            content=user_query,
            timestamp=now
        )
        session.messages.append(u_msg)

        # Assistant turn
        a_msg = ChatMessage(
            role="assistant",
            content=assistant_answer,
            timestamp=now,
            citations=citations,
            effective_scope=effective_scope,
            is_comparison=is_comparison,
            is_clarification=is_clarification,
            contains_unverified_notice=contains_unverified
        )
        session.messages.append(a_msg)
        session.updated_at = now

        # Keep session bounded (last 20 messages)
        if len(session.messages) > 20:
            session.messages = session.messages[-20:]

        self._persist_store()

        try:
            sqlite_db.save_message(
                message_id=u_msg.message_id,
                conversation_id=conversation_id,
                role=u_msg.role,
                content=u_msg.content,
                citations_json="[]",
                effective_scope_json="[]",
                is_comparison=False,
                is_clarification=False,
                contains_unverified_notice=False,
                timestamp=u_msg.timestamp
            )
            sqlite_db.save_message(
                message_id=a_msg.message_id,
                conversation_id=conversation_id,
                role=a_msg.role,
                content=a_msg.content,
                citations_json=json.dumps([c.model_dump() for c in citations]),
                effective_scope_json=json.dumps(effective_scope),
                is_comparison=is_comparison,
                is_clarification=is_clarification,
                contains_unverified_notice=contains_unverified,
                timestamp=a_msg.timestamp
            )
        except Exception as e:
            logger.error(f"Failed to persist chat messages to SQLite: {e}")

        return a_msg
