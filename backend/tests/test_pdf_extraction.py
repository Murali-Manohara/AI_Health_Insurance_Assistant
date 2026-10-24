import pytest
from pathlib import Path
from backend.app.services.pdf_extractor import PDFExtractor
from backend.app.core.config import settings

def test_extract_pdf_pages_real():
    extractor = PDFExtractor()
    pdf_path = settings.SOURCE_PDFS_DIR / "health_shield_basic.pdf"
    assert pdf_path.exists(), "Source PDF must exist for integration test"

    page_texts, ocr_needed, total_pages = extractor.extract_pdf_pages(pdf_path)
    assert total_pages == 10
    assert len(page_texts) == 10
    assert 1 in page_texts
    assert "HEALTH SHIELD" in page_texts[1].upper()
    assert isinstance(ocr_needed, list)

def test_ocr_detection_on_digital_pdf():
    extractor = PDFExtractor()
    pdf_path = settings.SOURCE_PDFS_DIR / "executive_employee_insurance_plan.pdf"
    assert pdf_path.exists()

    page_texts, ocr_needed, total_pages = extractor.extract_pdf_pages(pdf_path)
    assert total_pages == 18
    # Digital PDFs with abundant text should not require OCR
    assert len(ocr_needed) == 0
