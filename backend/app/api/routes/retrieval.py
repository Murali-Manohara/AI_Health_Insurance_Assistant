from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.api.schemas.retrieval import (
    RetrievalSearchRequest,
    RetrievalHealthResponse,
    RetrievalConfigResponse
)
from backend.app.services.retrieval_service import HybridRetrievalService, RRF_K_DEFAULT
from backend.app.services.auth_service import UserIdentity, AuthorizationService
from backend.app.api.deps import get_retrieval_service, get_auth_user
from backend.app.core.config import settings

router = APIRouter(prefix="/retrieval", tags=["Retrieval Diagnostics & Config"])

@router.get("/health", response_model=RetrievalHealthResponse)
def retrieval_health(
    retrieval_svc: HybridRetrievalService = Depends(get_retrieval_service)
):
    """Report health and status of ChromaDB, BM25 index, and embedding models."""
    bm25_status = retrieval_svc.bm25_service.get_status()
    total_chroma = retrieval_svc.chroma_service.collection.count()

    return RetrievalHealthResponse(
        status="HEALTHY" if total_chroma > 0 else "EMPTY_INDEX",
        chroma_mode=settings.CHROMA_MODE,
        chroma_collection=settings.CHROMA_COLLECTION_NAME,
        total_chunks=total_chroma,
        bm25_indexed_chunks=bm25_status["total_indexed_chunks"],
        embedding_model=settings.EMBEDDING_MODEL_NAME,
        embedding_dimension=settings.EMBEDDING_DIMENSION,
        llm_provider=settings.__dict__.get("LLM_PROVIDER", "grounded_synthesizer")
    )

@router.get("/config", response_model=RetrievalConfigResponse)
def retrieval_config():
    """Return supported retrieval strategies and system parameters."""
    return RetrievalConfigResponse(
        strategies_supported=["dense_vector", "bm25_lexical", "reciprocal_rank_fusion", "parent_expansion"],
        default_rrf_k=RRF_K_DEFAULT,
        embedding_model=settings.EMBEDDING_MODEL_NAME,
        embedding_dimension=settings.EMBEDDING_DIMENSION,
        max_query_tokens=500,
        default_top_k=5,
        plans_supported=["HS-BASIC-001", "HS-GOLD-001", "HS-PREMIUM-001", "EMP-INS-001"]
    )

@router.post("/search")
def diagnostic_search(
    req: RetrievalSearchRequest,
    user: UserIdentity = Depends(get_auth_user),
    retrieval_svc: HybridRetrievalService = Depends(get_retrieval_service)
):
    """
    Diagnostic search endpoint executing hybrid retrieval.
    Strictly filters results to user's authorized plans.
    """
    authorized_plans = list(AuthorizationService.get_authorized_plans(user.role))
    target_scope = req.effective_scope if req.effective_scope else authorized_plans

    results = retrieval_svc.retrieve(
        query=req.query,
        role=user.role,
        effective_scope=target_scope,
        top_k=req.top_k
    )
    return results
