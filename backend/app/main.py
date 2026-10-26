import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.logging_config import logger
from backend.app.api.routes import plans, upload, ingestion, conversations, retrieval, auth, admin_dashboard, eligibility, claim_predictor

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Server starts listening instantly (< 0.5s) to eliminate connection errors and 502s
    # Heavy RAG models warm up asynchronously in a background thread
    async def _background_warmup():
        try:
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                from backend.app.api.deps import get_rag_orchestrator
                await loop.run_in_executor(executor, get_rag_orchestrator)
            logger.info("Background RAG service warmup completed successfully.")
        except Exception as e:
            logger.warning(f"Background RAG warmup note: {e}")

    asyncio.create_task(_background_warmup())
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-oriented AI Insurance Assistant - Plan-Scoped RAG Chatbot",
    version="2.0.0",
    lifespan=lifespan
)

from backend.app.core.security_headers import SecurityHeadersMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware allowing whitelisted frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[ReqID: {req_id}] Unhandled server exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred. Please contact support with the request ID.",
            "request_id": req_id
        }
    )

# Mount Routers
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(admin_dashboard.router, prefix=settings.API_PREFIX)
app.include_router(eligibility.router, prefix=settings.API_PREFIX)
app.include_router(plans.router, prefix=settings.API_PREFIX)
app.include_router(upload.router, prefix=settings.API_PREFIX)
app.include_router(ingestion.router, prefix=settings.API_PREFIX)
app.include_router(conversations.router, prefix=settings.API_PREFIX)
app.include_router(retrieval.router, prefix=settings.API_PREFIX)
app.include_router(claim_predictor.router, prefix=settings.API_PREFIX)

@app.get("/api/health", tags=["Health"])
def health_check():
    """Application health endpoint."""
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "chroma_collection": settings.CHROMA_COLLECTION_NAME,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "embedding_dimensions": settings.EMBEDDING_DIMENSION
    }

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "AI Insurance Assistant - PDF Ingestion API is running.",
        "documentation": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
