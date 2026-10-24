import re
from typing import Optional
from backend.app.models.document import (
    SectionNode,
    SubsectionNode,
    ExtractedDocument,
    StructuredTable,
    CalculationBlock
)
from backend.app.models.chunk import (
    ParentChunk,
    ChildChunk,
    ChunkMetadata,
    ContentType
)
from backend.app.registry.plans import PlanInfo
from backend.app.core.config import settings
from backend.app.core.logging_config import logger

class TokenEstimator:
    """Estimates or counts tokens accurately for BGE-small embedding model."""
    def __init__(self):
        self.tokenizer = None
        try:
            from transformers import AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(settings.EMBEDDING_MODEL_NAME)
            logger.info(f"Loaded tokenizer for {settings.EMBEDDING_MODEL_NAME}")
        except Exception as e:
            logger.warning(f"Could not load HuggingFace tokenizer directly ({e}); using calibrated fallback.")

    def count_tokens(self, text: str) -> int:
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text, add_special_tokens=False))
            except Exception:
                pass
        # Calibrated fallback: ~1.3 tokens per whitespace word for technical insurance text
        words = len(text.split())
        return max(1, int(words * 1.3))

class ChunkingService:
    """
    Reusable, hierarchical, section-aware chunking service.
    Generates durable Parent section chunks and calibrated Child chunks (target 450-550 tokens).
    """

    def __init__(self):
        self.tokenizer = TokenEstimator()
        self.target_min = settings.TARGET_CHUNK_TOKENS_MIN
        self.target_max = settings.TARGET_CHUNK_TOKENS_MAX
        self.overlap = settings.CHUNK_OVERLAP_TOKENS

    def chunk_document(
        self,
        doc: ExtractedDocument,
        plan_info: PlanInfo,
        document_version: str = "1.0"
    ) -> tuple[list[ParentChunk], list[ChildChunk]]:
        logger.info(f"Chunking document {doc.filename} for plan {plan_info.plan_id}")
        parents: list[ParentChunk] = []
        children: list[ChildChunk] = []
        global_chunk_idx = 0

        for sec in doc.sections:
            # Deterministic Parent ID: e.g. HS-GOLD-001-SEC-05
            parent_id = f"{plan_info.plan_id}-{sec.section_id}"
            
            # 1. Build durable Parent Chunk Markdown
            parent_md_parts = [
                f"# {plan_info.plan_name} — {sec.heading_raw}",
                f"**Plan ID**: {plan_info.plan_id} | **Audience**: {plan_info.audience} | **Pages**: {sec.page_start}–{sec.page_end}\n"
            ]
            if sec.paragraphs:
                parent_md_parts.append("\n\n".join(sec.paragraphs))
            for sub in sec.subsections:
                parent_md_parts.append(f"### {sub.number} {sub.title}\n" + "\n\n".join(sub.paragraphs))
            for tbl in sec.tables:
                parent_md_parts.append(f"#### Table: {tbl.title}\n" + self._table_to_markdown(tbl))
            for calc in sec.calculations:
                parent_md_parts.append(f"#### Calculation: {calc.title}\n{calc.formula}")
            if sec.notes_and_conditions:
                parent_md_parts.append("#### Notes & Conditions:\n- " + "\n- ".join(sec.notes_and_conditions))

            full_parent_md = "\n\n".join(parent_md_parts)
            
            parent_chunk = ParentChunk(
                parent_id=parent_id,
                plan_id=plan_info.plan_id,
                section_number=sec.section_number,
                section_title=sec.title,
                heading_hierarchy=[plan_info.plan_name, sec.heading_raw],
                full_content_markdown=full_parent_md,
                source_page_start=sec.page_start,
                source_page_end=sec.page_end,
                child_chunk_ids=[]
            )

            # 2. Generate Child Chunks for this section
            sec_children: list[ChildChunk] = []

            # A. Process Prose Paragraphs
            if sec.paragraphs:
                prose_text = "\n\n".join(sec.paragraphs)
                prose_chunks = self._chunk_prose(
                    text=prose_text,
                    parent_id=parent_id,
                    sec=sec,
                    sub_title="",
                    plan_info=plan_info,
                    content_type="paragraph",
                    doc_version=document_version,
                    start_idx=global_chunk_idx
                )
                sec_children.extend(prose_chunks)
                global_chunk_idx += len(prose_chunks)

            # B. Process Subsections
            for sub in sec.subsections:
                if sub.paragraphs:
                    sub_text = "\n\n".join(sub.paragraphs)
                    sub_chunks = self._chunk_prose(
                        text=sub_text,
                        parent_id=parent_id,
                        sec=sec,
                        sub_title=f"{sub.number} {sub.title}",
                        plan_info=plan_info,
                        content_type="paragraph",
                        doc_version=document_version,
                        start_idx=global_chunk_idx
                    )
                    sec_children.extend(sub_chunks)
                    global_chunk_idx += len(sub_chunks)

            # C. Process Tables (Preserving structure, titles, headers, row labels, units)
            for tbl_idx, tbl in enumerate(sec.tables):
                tbl_chunks = self._chunk_table(
                    tbl=tbl,
                    parent_id=parent_id,
                    sec=sec,
                    plan_info=plan_info,
                    doc_version=document_version,
                    start_idx=global_chunk_idx,
                    tbl_index=tbl_idx + 1
                )
                sec_children.extend(tbl_chunks)
                global_chunk_idx += len(tbl_chunks)

            # D. Process Calculations (Formula, steps, inputs preserved together)
            for c_idx, calc in enumerate(sec.calculations):
                calc_chunk = self._chunk_calculation(
                    calc=calc,
                    parent_id=parent_id,
                    sec=sec,
                    plan_info=plan_info,
                    doc_version=document_version,
                    start_idx=global_chunk_idx,
                    calc_index=c_idx + 1
                )
                sec_children.append(calc_chunk)
                global_chunk_idx += 1

            # Link children back to parent
            parent_chunk.child_chunk_ids = [c.chunk_id for c in sec_children]
            parents.append(parent_chunk)
            children.extend(sec_children)

        logger.info(f"Generated {len(parents)} parents and {len(children)} children for {doc.filename}")
        return parents, children

    def _chunk_prose(
        self,
        text: str,
        parent_id: str,
        sec: SectionNode,
        sub_title: str,
        plan_info: PlanInfo,
        content_type: ContentType,
        doc_version: str,
        start_idx: int
    ) -> list[ChildChunk]:
        """Sliding window prose chunking targeting 450-550 tokens with 60-100 token overlap."""
        chunks: list[ChildChunk] = []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return chunks

        current_paras: list[str] = []
        current_tokens = 0
        local_idx = 1

        prefix = f"[{plan_info.plan_name} | {sec.heading_raw}" + (f" > {sub_title}]" if sub_title else "]") + "\n"
        prefix_tokens = self.tokenizer.count_tokens(prefix)

        for p in paragraphs:
            p_tokens = self.tokenizer.count_tokens(p)
            # If adding this paragraph fits nicely in target max
            if current_tokens + p_tokens + prefix_tokens <= self.target_max:
                current_paras.append(p)
                current_tokens += p_tokens
            else:
                if current_paras:
                    body = prefix + "\n\n".join(current_paras)
                    total_t = self.tokenizer.count_tokens(body)
                    chk_id = f"{parent_id}-CHK-{(start_idx + local_idx):03d}"
                    chunks.append(ChildChunk(
                        chunk_id=chk_id,
                        parent_section_id=parent_id,
                        content=body,
                        token_count=total_t,
                        metadata=ChunkMetadata(
                            plan_id=plan_info.plan_id,
                            plan_name=plan_info.plan_name,
                            plan_category=plan_info.plan_category,
                            audience=plan_info.audience,  # type: ignore
                            access_level=plan_info.access_level,
                            section_number=sec.section_number,
                            section_title=sec.title,
                            subsection_title=sub_title,
                            content_type=content_type,
                            parent_section_id=parent_id,
                            source_document=sec.heading_raw,  # Updated dynamically by metadata_service
                            source_page_start=sec.page_start,
                            source_page_end=sec.page_end,
                            document_version=doc_version,
                            data_status=plan_info.data_status_default,  # type: ignore
                            chunk_index=start_idx + local_idx
                        )
                    ))
                    local_idx += 1
                    # Retain last paragraph for overlap if within 60-100 tokens
                    if p_tokens <= self.overlap and current_paras:
                        current_paras = [current_paras[-1], p]
                        current_tokens = self.tokenizer.count_tokens("\n\n".join(current_paras))
                    else:
                        current_paras = [p]
                        current_tokens = p_tokens
                else:
                    # Single very long paragraph
                    current_paras = [p]
                    current_tokens = p_tokens

        if current_paras:
            body = prefix + "\n\n".join(current_paras)
            total_t = self.tokenizer.count_tokens(body)
            chk_id = f"{parent_id}-CHK-{(start_idx + local_idx):03d}"
            chunks.append(ChildChunk(
                chunk_id=chk_id,
                parent_section_id=parent_id,
                content=body,
                token_count=total_t,
                metadata=ChunkMetadata(
                    plan_id=plan_info.plan_id,
                    plan_name=plan_info.plan_name,
                    plan_category=plan_info.plan_category,
                    audience=plan_info.audience,  # type: ignore
                    access_level=plan_info.access_level,
                    section_number=sec.section_number,
                    section_title=sec.title,
                    subsection_title=sub_title,
                    content_type=content_type,
                    parent_section_id=parent_id,
                    source_document=sec.heading_raw,
                    source_page_start=sec.page_start,
                    source_page_end=sec.page_end,
                    document_version=doc_version,
                    data_status=plan_info.data_status_default,  # type: ignore
                    chunk_index=start_idx + local_idx
                )
            ))

        return chunks

    def _chunk_table(
        self,
        tbl: StructuredTable,
        parent_id: str,
        sec: SectionNode,
        plan_info: PlanInfo,
        doc_version: str,
        start_idx: int,
        tbl_index: int
    ) -> list[ChildChunk]:
        """Structure-preserving table chunking with headers, units, row labels and conditions."""
        chunks: list[ChildChunk] = []
        prefix = f"[{plan_info.plan_name} | {sec.heading_raw} | Table: {tbl.title}]\n"
        
        # Format table into markdown
        header_line = "| " + " | ".join(tbl.headers) + " |"
        sep_line = "| " + " | ".join(["---"] * len(tbl.headers)) + " |"
        
        # Group rows if table is large
        row_groups: list[list[list[str]]] = []
        current_group: list[list[str]] = []
        current_tokens = 0
        
        for row in tbl.rows:
            row_md = "| " + " | ".join(row) + " |"
            r_tokens = self.tokenizer.count_tokens(row_md)
            if current_tokens + r_tokens > self.target_max and current_group:
                row_groups.append(current_group)
                current_group = [row]
                current_tokens = r_tokens
            else:
                current_group.append(row)
                current_tokens += r_tokens
                
        if current_group:
            row_groups.append(current_group)

        for g_idx, group in enumerate(row_groups):
            rows_md = "\n".join(["| " + " | ".join(r) + " |" for r in group])
            table_body = f"{prefix}{header_line}\n{sep_line}\n{rows_md}"
            
            if tbl.conditions:
                table_body += "\n\n**Qualifying Conditions:**\n- " + "\n- ".join(tbl.conditions)
                
            total_t = self.tokenizer.count_tokens(table_body)
            chk_id = f"{parent_id}-TBL-{tbl_index:02d}-G{g_idx+1:02d}"
            
            chunks.append(ChildChunk(
                chunk_id=chk_id,
                parent_section_id=parent_id,
                content=table_body,
                token_count=total_t,
                metadata=ChunkMetadata(
                    plan_id=plan_info.plan_id,
                    plan_name=plan_info.plan_name,
                    plan_category=plan_info.plan_category,
                    audience=plan_info.audience,  # type: ignore
                    access_level=plan_info.access_level,
                    section_number=sec.section_number,
                    section_title=sec.title,
                    subsection_title=tbl.title,
                    content_type="table",
                    parent_section_id=parent_id,
                    source_document=sec.heading_raw,
                    source_page_start=tbl.page_start,
                    source_page_end=tbl.page_end,
                    document_version=doc_version,
                    data_status=plan_info.data_status_default,  # type: ignore
                    chunk_index=start_idx + len(chunks) + 1
                )
            ))
            
        return chunks

    def _chunk_calculation(
        self,
        calc: CalculationBlock,
        parent_id: str,
        sec: SectionNode,
        plan_info: PlanInfo,
        doc_version: str,
        start_idx: int,
        calc_index: int
    ) -> ChildChunk:
        """Self-contained calculation chunk preserving formula, inputs, steps, and limits."""
        prefix = f"[{plan_info.plan_name} | {sec.heading_raw} | Calculation: {calc.title}]\n"
        content_lines = [
            prefix,
            f"**Formula**: {calc.formula}",
            f"**Units / Currency**: {calc.units_or_currency}"
        ]
        if calc.steps:
            content_lines.append("**Calculation Steps / Variables**:")
            content_lines.extend([f"- {s}" for s in calc.steps])
        if calc.limits:
            content_lines.append("**Applicable Limits & Caps**:")
            content_lines.extend([f"- {lim}" for lim in calc.limits])
        if calc.conditions:
            content_lines.append("**Qualifying Conditions**:")
            content_lines.extend([f"- {c}" for c in calc.conditions])

        body = "\n".join(content_lines)
        total_t = self.tokenizer.count_tokens(body)
        chk_id = f"{parent_id}-CALC-{calc_index:02d}"

        return ChildChunk(
            chunk_id=chk_id,
            parent_section_id=parent_id,
            content=body,
            token_count=total_t,
            metadata=ChunkMetadata(
                plan_id=plan_info.plan_id,
                plan_name=plan_info.plan_name,
                plan_category=plan_info.plan_category,
                audience=plan_info.audience,  # type: ignore
                access_level=plan_info.access_level,
                section_number=sec.section_number,
                section_title=sec.title,
                subsection_title=calc.title,
                content_type="calculation",
                parent_section_id=parent_id,
                source_document=sec.heading_raw,
                source_page_start=calc.page_number,
                source_page_end=calc.page_number,
                document_version=doc_version,
                data_status=plan_info.data_status_default,  # type: ignore
                chunk_index=start_idx + 1
            )
        )

    def _table_to_markdown(self, tbl: StructuredTable) -> str:
        header = "| " + " | ".join(tbl.headers) + " |"
        sep = "| " + " | ".join(["---"] * len(tbl.headers)) + " |"
        rows = ["| " + " | ".join(r) + " |" for r in tbl.rows]
        return f"{header}\n{sep}\n" + "\n".join(rows)
