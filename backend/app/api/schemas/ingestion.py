from pydantic import BaseModel
from typing import Optional, Any

class IngestionMetrics(BaseModel):
    total_pages: int
    sections_detected: int
    tables_extracted: int
    calculations_detected: int
    parent_chunks_count: int
    child_chunks_count: int
    embeddings_count: int
    records_stored: int

class IngestionJobResponse(BaseModel):
    job_id: str
    filename: str
    plan_id: str
    status: str
    current_stage: str
    stages_completed: list[str]
    warnings: list[str]
    errors: list[str]
    total_duration_sec: float
    content_hash: str
    is_duplicate: bool
    metrics: IngestionMetrics
    coverage_report: dict[str, Any]

class HistoryItem(BaseModel):
    timestamp: str
    job_id: str
    source_document: str
    plan_id: str
    content_hash: str
    status: str
    chunks_stored: int
    duration_sec: float
    errors: list[str]
