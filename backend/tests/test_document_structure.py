import pytest
from backend.app.services.pdf_extractor import PDFExtractor
from backend.app.services.table_extractor import TableExtractor
from backend.app.services.document_structure import DocumentStructureParser
from backend.app.core.config import settings

def test_detect_17_sections_in_gold():
    extractor = PDFExtractor()
    tbl_extractor = TableExtractor()
    parser = DocumentStructureParser()

    pdf_path = settings.SOURCE_PDFS_DIR / "health_shield_gold.pdf"
    assert pdf_path.exists()

    page_texts, ocr_pages, total_pages = extractor.extract_pdf_pages(pdf_path)
    tables = tbl_extractor.extract_tables(pdf_path)
    doc_model = parser.parse_document(
        filename="health_shield_gold.pdf",
        page_texts=page_texts,
        tables=tables,
        ocr_needed_pages=ocr_pages
    )

    assert doc_model.total_pages == 11
    # Check that sections were detected
    detected_sec_nums = {s.section_number for s in doc_model.sections}
    # All 17 sections should be present
    for sec_i in range(1, 18):
        assert str(sec_i) in detected_sec_nums, f"Section {sec_i} was not detected"

def test_subsections_and_disclaimers_in_employee():
    extractor = PDFExtractor()
    tbl_extractor = TableExtractor()
    parser = DocumentStructureParser()

    pdf_path = settings.SOURCE_PDFS_DIR / "executive_employee_insurance_plan.pdf"
    assert pdf_path.exists()

    page_texts, ocr_pages, total_pages = extractor.extract_pdf_pages(pdf_path)
    tables = tbl_extractor.extract_tables(pdf_path)
    doc_model = parser.parse_document(
        filename="executive_employee_insurance_plan.pdf",
        page_texts=page_texts,
        tables=tables,
        ocr_needed_pages=ocr_pages
    )

    # Verify that disclaimers are preserved
    all_disclaimers = [d for s in doc_model.sections for d in s.notes_and_conditions]
    assert len(all_disclaimers) > 0
    # Confirm illustrative keywords are retained
    combined_disclaimers = " ".join(all_disclaimers).lower()
    assert any(term in combined_disclaimers for term in ["not verified", "not defined", "illustrative"])
