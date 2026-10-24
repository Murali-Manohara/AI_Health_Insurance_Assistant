import pytest
from backend.app.services.chroma_service import ChromaStorageService
from backend.app.models.chunk import ValidatedChunk, ParentChunk

def test_staged_replace_and_readback():
    chroma_svc = ChromaStorageService()
    test_doc = "test_plan_sample.pdf"
    
    # 1. Create a dummy validated chunk
    chunk = ValidatedChunk(
        chunk_id="TEST-SEC-01-CHK-001",
        content="Test content for persistent storage verification.",
        metadata={
            "plan_id": "HS-TEST-001",
            "plan_name": "Test Plan",
            "plan_category": "Test",
            "audience": "customer",
            "access_level": "customer",
            "section_number": "1",
            "section_title": "Test Section",
            "subsection_title": "",
            "content_type": "paragraph",
            "parent_section_id": "TEST-SEC-01",
            "source_document": test_doc,
            "source_page_start": 1,
            "source_page_end": 1,
            "document_version": "1.0",
            "data_status": "verified",
            "chunk_index": 1
        },
        embedding=[0.05] * 384
    )

    parent = ParentChunk(
        parent_id="TEST-SEC-01",
        plan_id="HS-TEST-001",
        section_number="1",
        section_title="Test Section",
        heading_hierarchy=["Test Plan", "Section 1"],
        full_content_markdown="# Test Section\nFull text here.",
        source_page_start=1,
        source_page_end=1,
        child_chunk_ids=["TEST-SEC-01-CHK-001"]
    )

    res = chroma_svc.staged_replace_document_chunks(
        source_filename=test_doc,
        plan_id="HS-TEST-001",
        chunks=[chunk],
        parents=[parent]
    )

    assert res["inserted_count"] == 1
    assert chroma_svc.verify_records_by_ids(["TEST-SEC-01-CHK-001"])

    # Clean up test chunk so it doesn't pollute knowledge base
    chroma_svc.collection.delete(ids=["TEST-SEC-01-CHK-001"])
