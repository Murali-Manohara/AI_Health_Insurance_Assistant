import pytest
from backend.app.services.metadata_service import MetadataService
from backend.app.models.chunk import ChildChunk, ChunkMetadata
from backend.app.registry.plans import get_plan_by_id

def test_flat_chromadb_metadata_compliance():
    meta_service = MetadataService()
    plan_info = get_plan_by_id("HS-GOLD-001")

    chunk = ChildChunk(
        chunk_id="HS-GOLD-001-SEC-05-CHK-001",
        parent_section_id="HS-GOLD-001-SEC-05",
        content="Major surgery benefit covers up to 100% of sum insured.",
        token_count=120,
        metadata=ChunkMetadata(
            plan_id=plan_info.plan_id,
            plan_name=plan_info.plan_name,
            plan_category=plan_info.plan_category,
            audience=plan_info.audience,  # type: ignore
            access_level=plan_info.access_level,
            section_number="5",
            section_title="Major Surgery Benefit",
            subsection_title="",
            content_type="paragraph",
            parent_section_id="HS-GOLD-001-SEC-05",
            source_document="dummy.pdf",
            source_page_start=4,
            source_page_end=4,
            document_version="1.0",
            data_status="verified",
            chunk_index=1
        )
    )

    flat_dict = meta_service.finalize_metadata(chunk, plan_info, "health_shield_gold.pdf")

    # Verify all 16 required keys are present
    assert len(flat_dict) == 16
    assert flat_dict["source_document"] == "health_shield_gold.pdf"
    assert flat_dict["plan_id"] == "HS-GOLD-001"
    assert flat_dict["data_status"] == "verified"

    # Verify strictly primitive flat types
    for k, v in flat_dict.items():
        assert isinstance(v, (str, int, float, bool)), f"Key {k} has non-primitive type {type(v)}"

def test_employee_metadata_illustrative_flag():
    meta_service = MetadataService()
    emp_plan = get_plan_by_id("EMP-INS-001")

    chunk = ChildChunk(
        chunk_id="EMP-INS-001-SEC-05-CHK-001",
        parent_section_id="EMP-INS-001-SEC-05",
        content="Schedule of benefits is illustrative and not verified.",
        token_count=100,
        metadata=ChunkMetadata(
            plan_id=emp_plan.plan_id,
            plan_name=emp_plan.plan_name,
            plan_category=emp_plan.plan_category,
            audience=emp_plan.audience,  # type: ignore
            access_level=emp_plan.access_level,
            section_number="5",
            section_title="Benefits",
            subsection_title="",
            content_type="paragraph",
            parent_section_id="EMP-INS-001-SEC-05",
            source_document="dummy.pdf",
            source_page_start=1,
            source_page_end=1,
            document_version="1.0",
            data_status="verified",
            chunk_index=1
        )
    )

    flat_dict = meta_service.finalize_metadata(chunk, emp_plan, "executive_employee_insurance_plan.pdf")
    assert flat_dict["data_status"] == "illustrative_unverified"
    assert flat_dict["audience"] == "employee"
