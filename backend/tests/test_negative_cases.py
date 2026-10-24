import pytest
from fastapi import HTTPException
from backend.app.utils.security import validate_pdf_bytes
from backend.app.services.validation_service import ValidationService
from backend.app.registry.plans import get_plan_by_id

def test_reject_non_pdf_file():
    fake_txt_bytes = b"Hello world, this is a plain text file."
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_bytes(fake_txt_bytes, "policy.txt")
    assert exc_info.value.status_code == 400
    assert "PDF header signature" in exc_info.value.detail

def test_reject_empty_file():
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_bytes(b"", "empty.pdf")
    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail.lower()

def test_reject_mismatched_plan_identity():
    validator = ValidationService()
    # Selected plan is Gold, but document text explicitly says Health Shield - Basic
    doc_sample = "HEALTH SHIELD - BASIC | Plan ID: HS-BASIC-001 | Category: Basic"
    gold_plan = get_plan_by_id("HS-GOLD-001")
    
    result = validator.validate_document_identity(doc_sample, gold_plan)
    assert not result.is_valid
    assert len(result.errors) > 0
    assert "Document identity mismatch" in result.errors[0]
