from pathlib import Path
from typing import Optional
import pdfplumber
from backend.app.models.document import StructuredTable
from backend.app.core.logging_config import logger

class TableExtractor:
    """Extracts tables from PDFs using pdfplumber, preserving row-column alignment and context."""

    def extract_tables(self, file_path: Path | str) -> list[StructuredTable]:
        path_str = str(file_path)
        logger.info(f"Extracting tables from {path_str} with pdfplumber")
        structured_tables: list[StructuredTable] = []
        
        try:
            with pdfplumber.open(path_str) as pdf:
                table_counter = 0
                prev_table: Optional[StructuredTable] = None
                
                for pno, page in enumerate(pdf.pages):
                    page_num = pno + 1
                    extracted_page_tables = page.extract_tables()
                    
                    if not extracted_page_tables:
                        continue
                        
                    for raw_table in extracted_page_tables:
                        # Clean and filter empty rows/columns
                        cleaned_rows: list[list[str]] = []
                        for row in raw_table:
                            if not row:
                                continue
                            cleaned_cells = [str(cell).strip() if cell is not None else "" for cell in row]
                            # Keep row if not completely empty
                            if any(len(c) > 0 for c in cleaned_cells):
                                cleaned_rows.append(cleaned_cells)
                                
                        if len(cleaned_rows) < 2:
                            # Not a useful multi-row table
                            continue
                            
                        table_counter += 1
                        headers = cleaned_rows[0]
                        data_rows = cleaned_rows[1:]
                        
                        # Multi-page continuation detection:
                        # If headers match previous table and page is consecutive
                        if prev_table and prev_table.page_end == page_num - 1 and prev_table.headers == headers:
                            logger.info(f"Detected table continuation from page {prev_table.page_end} to page {page_num}")
                            prev_table.rows.extend(data_rows)
                            prev_table.page_end = page_num
                            continue
                            
                        # Infer table context title from first header or preceding text
                        table_title = f"Table {table_counter}: {' / '.join([h for h in headers if h][:3])}"
                        
                        st = StructuredTable(
                            table_id=f"TBL-{table_counter:02d}",
                            title=table_title,
                            headers=headers,
                            rows=data_rows,
                            page_start=page_num,
                            page_end=page_num,
                            section_context="",
                            footnotes=[],
                            conditions=[]
                        )
                        structured_tables.append(st)
                        prev_table = st
                        
        except Exception as e:
            logger.error(f"Error during table extraction: {e}")
            # Do not crash entire extraction; return what was found
            
        logger.info(f"Extracted {len(structured_tables)} structured tables from {path_str}")
        return structured_tables
