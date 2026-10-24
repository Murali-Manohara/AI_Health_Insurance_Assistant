from typing import Any
from backend.app.models.chunk import ChildChunk, ChunkMetadata
from backend.app.registry.plans import PlanInfo
from backend.app.core.logging_config import logger

class MetadataService:
    """Enriches and validates flat ChromaDB metadata dictionaries for child chunks."""

    REQUIRED_KEYS = {
        "plan_id", "plan_name", "plan_category", "audience", "access_level",
        "section_number", "section_title", "subsection_title", "content_type",
        "parent_section_id", "source_document", "source_page_start",
        "source_page_end", "document_version", "data_status", "chunk_index"
    }

    def finalize_metadata(
        self,
        chunk: ChildChunk,
        plan_info: PlanInfo,
        actual_source_filename: str
    ) -> dict[str, str | int | float | bool]:
        """Populate actual source filename and generate verified flat dictionary."""
        # 1. Update source_document to actual uploaded filename
        chunk.metadata.source_document = actual_source_filename
        chunk.metadata.plan_id = plan_info.plan_id
        chunk.metadata.plan_name = plan_info.plan_name
        chunk.metadata.plan_category = plan_info.plan_category
        chunk.metadata.audience = plan_info.audience  # type: ignore
        chunk.metadata.access_level = plan_info.access_level

        # 2. Check for literal unverified keywords in the chunk body
        chunk_content_lower = chunk.content.lower()
        if (
            plan_info.plan_id == "EMP-INS-001"
            or "not verified" in chunk_content_lower
            or "not defined" in chunk_content_lower
            or "illustrative" in chunk_content_lower
        ):
            chunk.metadata.data_status = "illustrative_unverified"

        # 3. Convert to flat primitive dict
        meta_dict = chunk.metadata.to_chroma_metadata()

        # 4. Validate types and required keys
        missing = self.REQUIRED_KEYS - set(meta_dict.keys())
        if missing:
            raise ValueError(f"Missing required metadata fields in chunk {chunk.chunk_id}: {missing}")

        for k, v in meta_dict.items():
            if not isinstance(v, (str, int, float, bool)):
                raise TypeError(
                    f"Invalid metadata type for key '{k}' in chunk {chunk.chunk_id}: {type(v)}. "
                    f"ChromaDB requires flat primitive types (str, int, float, bool)."
                )

        return meta_dict
