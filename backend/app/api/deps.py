import threading
from typing import Optional
from fastapi import Depends, Request
from backend.app.services.ingestion_orchestrator import IngestionOrchestrator
from backend.app.services.rag_orchestrator import RAGOrchestrator
from backend.app.services.retrieval_service import HybridRetrievalService
from backend.app.services.auth_service import UserIdentity, get_current_user, require_admin_user

# Thread-safe lazy singletons (avoid blocking FastAPI server startup)
_ingestion_lock = threading.Lock()
_rag_lock = threading.Lock()
_ingestion_orchestrator: Optional[IngestionOrchestrator] = None
_rag_orchestrator: Optional[RAGOrchestrator] = None

def get_orchestrator() -> IngestionOrchestrator:
    global _ingestion_orchestrator
    if _ingestion_orchestrator is None:
        with _ingestion_lock:
            if _ingestion_orchestrator is None:
                _ingestion_orchestrator = IngestionOrchestrator()
    return _ingestion_orchestrator

def get_rag_orchestrator() -> RAGOrchestrator:
    global _rag_orchestrator
    if _rag_orchestrator is None:
        with _rag_lock:
            if _rag_orchestrator is None:
                _rag_orchestrator = RAGOrchestrator()
    return _rag_orchestrator

def get_retrieval_service() -> HybridRetrievalService:
    return get_rag_orchestrator().retrieval_service

def get_auth_user(request: Request) -> UserIdentity:
    return get_current_user(request)

def get_admin_user(request: Request) -> UserIdentity:
    return require_admin_user(request)

# Module-level __getattr__ for backward compatibility
def __getattr__(name: str):
    if name == "ingestion_orchestrator":
        return get_orchestrator()
    if name == "rag_orchestrator":
        return get_rag_orchestrator()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
