from typing import Literal, Optional
from pydantic import BaseModel, Field

ContentType = Literal["paragraph", "list", "table", "table_row", "calculation", "condition"]
DataStatus = Literal["verified", "illustrative_unverified", "unverified"]
AudienceType = Literal["customer", "employee"]

class ChunkMetadata(BaseModel):
    plan_id: str
    plan_name: str
    plan_category: str
    audience: AudienceType
    access_level: str
    section_number: str
    section_title: str
    subsection_title: str = ""
    content_type: ContentType
    parent_section_id: str
    source_document: str
    source_page_start: int
    source_page_end: int
    document_version: str = "1.0"
    data_status: DataStatus
    chunk_index: int
    
    def to_chroma_metadata(self) -> dict[str, str | int | float | bool]:
        """Convert to ChromaDB-safe flat primitive dictionary."""
        return {
            "plan_id": str(self.plan_id),
            "plan_name": str(self.plan_name),
            "plan_category": str(self.plan_category),
            "audience": str(self.audience),
            "access_level": str(self.access_level),
            "section_number": str(self.section_number),
            "section_title": str(self.section_title),
            "subsection_title": str(self.subsection_title or ""),
            "content_type": str(self.content_type),
            "parent_section_id": str(self.parent_section_id),
            "source_document": str(self.source_document),
            "source_page_start": int(self.source_page_start),
            "source_page_end": int(self.source_page_end),
            "document_version": str(self.document_version),
            "data_status": str(self.data_status),
            "chunk_index": int(self.chunk_index),
        }

class ParentChunk(BaseModel):
    parent_id: str
    plan_id: str
    section_number: str
    section_title: str
    heading_hierarchy: list[str]
    full_content_markdown: str
    source_page_start: int
    source_page_end: int
    child_chunk_ids: list[str] = Field(default_factory=list)

class ChildChunk(BaseModel):
    chunk_id: str
    parent_section_id: str
    content: str
    token_count: int
    metadata: ChunkMetadata

class ValidatedChunk(BaseModel):
    chunk_id: str
    content: str
    metadata: dict[str, str | int | float | bool]
    embedding: list[float]
