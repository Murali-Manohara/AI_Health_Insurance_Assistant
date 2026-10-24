from pydantic import BaseModel, Field
from typing import Optional

class RetrievalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    effective_scope: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)

class RetrievalHealthResponse(BaseModel):
    status: str
    chroma_mode: str
    chroma_collection: str
    total_chunks: int
    bm25_indexed_chunks: int
    embedding_model: str
    embedding_dimension: int
    llm_provider: str

class RetrievalConfigResponse(BaseModel):
    strategies_supported: list[str]
    default_rrf_k: int
    embedding_model: str
    embedding_dimension: int
    max_query_tokens: int
    default_top_k: int
    plans_supported: list[str]
