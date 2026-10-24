import pytest
from backend.app.services.chunking_service import ChunkingService
from backend.app.services.pdf_extractor import PDFExtractor
from backend.app.services.table_extractor import TableExtractor
from backend.app.services.document_structure import DocumentStructureParser
from backend.app.registry.plans import get_plan_by_id
from backend.app.core.config import settings

def test_hierarchical_chunking_parent_child():
    extractor = PDFExtractor()
    tbl_extractor = TableExtractor()
    parser = DocumentStructureParser()
    chunker = ChunkingService()
    plan_info = get_plan_by_id("HS-BASIC-001")

    pdf_path = settings.SOURCE_PDFS_DIR / "health_shield_basic.pdf"
    assert pdf_path.exists()

    page_texts, ocr_pages, total_pages = extractor.extract_pdf_pages(pdf_path)
    tables = tbl_extractor.extract_tables(pdf_path)
    doc_model = parser.parse_document("health_shield_basic.pdf", page_texts, tables, ocr_pages)

    parents, children = chunker.chunk_document(doc_model, plan_info)

    assert len(parents) > 0
    assert len(children) > 0

    # Verify Parent ID format: HS-BASIC-001-SEC-01
    assert parents[0].parent_id.startswith("HS-BASIC-001-SEC-")
    assert parents[0].full_content_markdown.startswith("# Health Shield – Basic")

    # Verify Child chunk references valid parent
    parent_ids = {p.parent_id for p in parents}
    for c in children:
        assert c.parent_section_id in parent_ids
        assert c.token_count > 0
        assert c.metadata.plan_id == "HS-BASIC-001"
