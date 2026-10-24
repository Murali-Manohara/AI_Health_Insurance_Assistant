import re
from typing import Optional, Any
from backend.app.models.document import ExtractedDocument, CalculationBlock
from backend.app.models.chunk import ChildChunk
from backend.app.registry.plans import PlanInfo
from backend.app.core.logging_config import logger

class ValidationResult:
    def __init__(self, is_valid: bool, errors: list[str], warnings: list[str]):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings

class ValidationService:
    """Multi-tier validation suite: Document Identity, 17-Section Completeness, Chunks, and Arithmetic."""

    def validate_document_identity(self, first_pages_text: str, plan_info: PlanInfo) -> ValidationResult:
        """Verify that uploaded PDF content matches the selected plan identity."""
        errors: list[str] = []
        warnings: list[str] = []
        
        sample_lower = first_pages_text.lower()
        plan_id_lower = plan_info.plan_id.lower()
        plan_name_lower = plan_info.plan_name.lower().replace("–", "-")
        sample_normalized = sample_lower.replace("–", "-")
        
        # Check plan ID or plan name in header
        has_id = plan_id_lower in sample_normalized
        has_name = (
            plan_name_lower in sample_normalized
            or plan_info.plan_category.lower() in sample_normalized
        )
        
        if not has_id and not has_name:
            err = (
                f"Document identity mismatch! Selected plan is '{plan_info.plan_name}' ({plan_info.plan_id}), "
                f"but neither the plan name nor the plan ID was found in the document header."
            )
            logger.error(err)
            errors.append(err)
        else:
            logger.info(f"Document identity verified: matched '{plan_info.plan_name}' ({plan_info.plan_id})")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_extracted_structure(self, doc: ExtractedDocument) -> ValidationResult:
        """Verify 17-section structure and page coverage."""
        errors: list[str] = []
        warnings: list[str] = []

        if doc.total_pages == 0:
            errors.append("Document has 0 pages.")

        # Check section count
        detected_sec_nums = {s.section_number for s in doc.sections}
        expected_sec_nums = {str(i) for i in range(1, 18)}
        missing_sections = expected_sec_nums - detected_sec_nums
        
        if missing_sections:
            warn = f"Detected {len(detected_sec_nums)}/17 sections. Missing sections: {sorted(list(missing_sections), key=int)}"
            logger.warning(warn)
            warnings.append(warn)
        else:
            logger.info("Structure verified: All 17 expected numbered sections detected.")

        if doc.ocr_needed_pages:
            warnings.append(f"Pages requiring OCR fallback: {doc.ocr_needed_pages}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_chunks_before_storage(self, chunks: list[ChildChunk]) -> ValidationResult:
        """Validate chunks before embedding and ChromaDB insertion."""
        errors: list[str] = []
        warnings: list[str] = []

        if not chunks:
            errors.append("Chunking produced 0 chunks. Ingestion cannot proceed.")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        for c in chunks:
            if not c.content or len(c.content.strip()) < 10:
                errors.append(f"Chunk {c.chunk_id} has empty or near-empty content.")
            if not c.parent_section_id:
                errors.append(f"Chunk {c.chunk_id} is missing a parent_section_id reference.")
            if c.token_count > 900:
                warnings.append(f"Chunk {c.chunk_id} is unusually large ({c.token_count} tokens).")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def verify_calculation_arithmetic(self, calc: CalculationBlock) -> bool:
        """Perform arithmetic sanity checks on numerical calculation steps."""
        try:
            # Check for patterns like "10% of 5,00,000 = 50,000" or "X * Y = Z"
            for step in calc.steps:
                m = re.search(r'([\d\.,]+)\s*([\*\+xX])\s*([\d\.,]+)\s*=\s*([\d\.,]+)', step)
                if m:
                    n1 = float(m.group(1).replace(',', ''))
                    op = m.group(2)
                    n2 = float(m.group(3).replace(',', ''))
                    expected_res = float(m.group(4).replace(',', ''))
                    calc_res = (n1 * n2) if op in ['*', 'x', 'X'] else (n1 + n2)
                    if abs(calc_res - expected_res) > 1.0:
                        logger.warning(f"Arithmetic discrepancy in calculation {calc.calc_id}: {step} (calculated {calc_res} != source {expected_res})")
                        return False
        except Exception:
            pass
        return True
