from fastapi import Depends, Request
from backend.app.services.ingestion_orchestrator import IngestionOrchestrator
from backend.app.services.rag_orchestrator import RAGOrchestrator
from backend.app.services.retrieval_service import HybridRetrievalService
from backend.app.services.auth_service import UserIdentity, get_current_user, require_admin_user

# Global service singletons
ingestion_orchestrator = IngestionOrchestrator()
rag_orchestrator = RAGOrchestrator()

def get_orchestrator() -> IngestionOrchestrator:
    return ingestion_orchestrator

def get_rag_orchestrator() -> RAGOrchestrator:
    return rag_orchestrator

def get_retrieval_service() -> HybridRetrievalService:
    return rag_orchestrator.retrieval_service

def get_auth_user(request: Request) -> UserIdentity:
    return get_current_user(request)

def get_admin_user(request: Request) -> UserIdentity:
    return require_admin_user(request)
