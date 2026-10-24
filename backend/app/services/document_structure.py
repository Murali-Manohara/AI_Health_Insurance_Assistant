import re
from typing import Optional
from backend.app.models.document import (
    SectionNode,
    SubsectionNode,
    ExtractedDocument,
    StructuredTable,
    CalculationBlock
)
from backend.app.core.logging_config import logger

class DocumentStructureParser:
    """Parses raw extracted text and tables into the 17-section hierarchical Document Model."""

    # Section regex matching strictly "SECTION 1:", "SECTION 5: MAJOR SURGERY BENEFIT", etc.
    SECTION_PATTERN = re.compile(
        r"(?:^|\n)\s*SECTION\s+(\d{1,2})[:\.\s\-]+([^\n]+)",
        re.IGNORECASE | re.MULTILINE
    )
    
    # Subsection regex matching e.g. "11.1 Specific Illness Waiting Period" or "14.2 Calculation Steps"
    SUBSECTION_PATTERN = re.compile(
        r"(?:^|\n)\s*(\d{1,2}\.\d{1,2})\s+([^\n]+)",
        re.MULTILINE
    )

    # Calculation detection pattern
    CALC_KEYWORD_PATTERN = re.compile(
        r"(?:formula|calculation|input|steps?|sum insured|payout percentage|benefit amount)",
        re.IGNORECASE
    )

    def parse_document(
        self,
        filename: str,
        page_texts: dict[int, str],
        tables: list[StructuredTable],
        ocr_needed_pages: list[int]
    ) -> ExtractedDocument:
        logger.info(f"Parsing 17-section document structure for {filename}")
        
        # Build unified text with page markers
        combined_text = ""
        page_offsets: list[tuple[int, int, int]] = []  # (start_char, end_char, page_num)
        
        for pno in sorted(page_texts.keys()):
            p_text = page_texts[pno]
            start_idx = len(combined_text)
            combined_text += p_text + "\n\n"
            end_idx = len(combined_text)
            page_offsets.append((start_idx, end_idx, pno))
            
        def get_page_for_pos(pos: int) -> int:
            for s_idx, e_idx, pno in page_offsets:
                if s_idx <= pos < e_idx:
                    return pno
            return page_offsets[-1][2] if page_offsets else 1

        # Locate all section headers
        matches = list(self.SECTION_PATTERN.finditer(combined_text))
        sections: list[SectionNode] = []
        
        for i, match in enumerate(matches):
            sec_num_str = match.group(1)
            sec_title_str = (match.group(2) or "").strip()
            
            # Start position of this section
            sec_start_pos = match.start()
            sec_end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(combined_text)
            
            sec_text = combined_text[sec_start_pos:sec_end_pos].strip()
            p_start = get_page_for_pos(sec_start_pos)
            p_end = get_page_for_pos(sec_end_pos - 1)
            
            sec_id = f"SEC-{int(sec_num_str):02d}"
            
            # Detect subsections in this section
            subsections = self._parse_subsections(sec_text, sec_id, p_start, p_end)
            
            # Extract paragraphs and lists
            paragraphs, lists = self._extract_paragraphs_and_lists(sec_text)
            
            # Associate matching tables with this section based on page span
            sec_tables = [
                tbl for tbl in tables
                if (p_start <= tbl.page_start <= p_end or p_start <= tbl.page_end <= p_end)
            ]
            for tbl in sec_tables:
                tbl.section_context = f"{sec_num_str}: {sec_title_str}"
                
            # Detect calculation blocks
            sec_calcs = self._detect_calculations(sec_text, sec_id, p_start)
            
            # Collect condition / disclaimers
            disclaimers = self._extract_disclaimers(sec_text)
            
            node = SectionNode(
                section_id=sec_id,
                section_number=str(int(sec_num_str)),
                title=sec_title_str,
                page_start=p_start,
                page_end=p_end,
                heading_raw=match.group(0).strip(),
                paragraphs=paragraphs,
                lists=lists,
                subsections=subsections,
                tables=sec_tables,
                calculations=sec_calcs,
                notes_and_conditions=disclaimers
            )
            sections.append(node)
            
        # Collect all calculations across all sections
        all_calcs = [c for s in sections for c in s.calculations]
        
        logger.info(f"Structure parser detected {len(sections)} sections in {filename}")
        
        return ExtractedDocument(
            filename=filename,
            total_pages=len(page_texts),
            full_text=combined_text,
            sections=sections,
            tables=tables,
            calculations=all_calcs,
            ocr_needed_pages=ocr_needed_pages,
            raw_page_texts=page_texts
        )

    def _parse_subsections(self, text: str, parent_sec_id: str, p_start: int, p_end: int) -> list[SubsectionNode]:
        sub_matches = list(self.SUBSECTION_PATTERN.finditer(text))
        subsections: list[SubsectionNode] = []
        for j, sm in enumerate(sub_matches):
            sub_num = sm.group(1)
            sub_title = sm.group(2).strip()
            s_start = sm.start()
            s_end = sub_matches[j + 1].start() if j + 1 < len(sub_matches) else len(text)
            sub_body = text[s_start:s_end].strip()
            
            paras, lists = self._extract_paragraphs_and_lists(sub_body)
            sub_node = SubsectionNode(
                subsection_id=f"{parent_sec_id}-SUB-{sub_num.replace('.', '_')}",
                number=sub_num,
                title=sub_title,
                page_start=p_start,
                page_end=p_end,
                paragraphs=paras,
                lists=lists,
                tables=[],
                calculations=[]
            )
            subsections.append(sub_node)
        return subsections

    def _extract_paragraphs_and_lists(self, text: str) -> tuple[list[str], list[list[str]]]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        paragraphs: list[str] = []
        lists: list[list[str]] = []
        current_list: list[str] = []
        current_para: list[str] = []
        
        for line in lines:
            # Bullet or numbered item
            if re.match(r"^(\*|\-|\u2022|\d+[\.\)])\s+", line):
                if current_para:
                    paragraphs.append(" ".join(current_para))
                    current_para = []
                current_list.append(line)
            else:
                if current_list:
                    lists.append(current_list)
                    current_list = []
                current_para.append(line)
                
        if current_para:
            paragraphs.append(" ".join(current_para))
        if current_list:
            lists.append(current_list)
            
        return paragraphs, lists

    def _detect_calculations(self, text: str, sec_id: str, page_num: int) -> list[CalculationBlock]:
        """Detect formulas, arithmetic steps, and calculation definitions."""
        calcs: list[CalculationBlock] = []
        lines = text.splitlines()
        calc_lines: list[str] = []
        in_calc = False
        
        for line in lines:
            stripped = line.strip()
            if any(k in stripped.lower() for k in ["formula:", "calculation:", "illustrative calculation", "payout ="]):
                in_calc = True
            if in_calc:
                calc_lines.append(stripped)
                if len(calc_lines) > 1 and stripped == "":
                    # Block finished
                    block_text = "\n".join(calc_lines).strip()
                    if len(block_text) > 30:
                        calcs.append(CalculationBlock(
                            calc_id=f"{sec_id}-CALC-{len(calcs)+1:02d}",
                            title=calc_lines[0] if calc_lines else "Policy Calculation",
                            formula=block_text[:200],
                            variables={},
                            inputs={},
                            steps=[l for l in calc_lines if "=" in l or ":" in l],
                            result="",
                            units_or_currency="INR / %",
                            limits=[],
                            conditions=[],
                            page_number=page_num
                        ))
                    calc_lines = []
                    in_calc = False
                    
        return calcs

    def _extract_disclaimers(self, text: str) -> list[str]:
        """Collect all explicit disclaimers and condition qualifiers."""
        disclaimers = []
        for line in text.splitlines():
            l_lower = line.strip().lower()
            if any(term in l_lower for term in [
                "not defined", "not verified", "not confirmed", "illustrative",
                "subject to policy conditions", "exclusion", "waiting period"
            ]):
                disclaimers.append(line.strip())
        return disclaimers
