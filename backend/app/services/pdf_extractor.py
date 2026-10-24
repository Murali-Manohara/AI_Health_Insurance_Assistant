from pathlib import Path
from typing import Optional
import pymupdf
from backend.app.core.logging_config import logger

class PDFExtractor:
    """Extracts raw text, blocks, and layout data page-by-page from PDFs using PyMuPDF."""
    
    def __init__(self):
        pass

    def extract_pdf_pages(self, file_path: Path | str) -> tuple[dict[int, str], list[int], int]:
        """
        Extract page text and detect pages needing OCR.
        Returns:
            page_texts: dict mapping page_number (1-indexed) -> text
            ocr_needed_pages: list of page numbers requiring OCR
            total_pages: total number of pages
        """
        path_str = str(file_path)
        logger.info(f"Opening PDF for extraction: {path_str}")
        
        try:
            doc = pymupdf.open(path_str)
        except Exception as e:
            logger.error(f"Failed to open PDF {path_str}: {e}")
            raise ValueError(f"Could not open or parse PDF: {str(e)}")
            
        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            raise ValueError("PDF document has 0 pages.")
            
        page_texts: dict[int, str] = {}
        ocr_needed_pages: list[int] = []
        
        for pno in range(total_pages):
            page = doc[pno]
            text = page.get_text("text").strip()
            page_num = pno + 1
            
            # OCR detection rule: text < 50 chars but has raster images
            image_list = page.get_images()
            if len(text) < 50 and len(image_list) > 0:
                logger.warning(f"Page {page_num} has only {len(text)} chars with {len(image_list)} images -> Needs OCR")
                ocr_needed_pages.append(page_num)
                # Attempt basic OCR fallback if available in PyMuPDF
                try:
                    ocr_page = page.get_textpage_ocr()
                    ocr_text = ocr_page.extractText().strip()
                    if len(ocr_text) > len(text):
                        text = ocr_text
                        logger.info(f"OCR successfully extracted {len(ocr_text)} characters on page {page_num}")
                except Exception as ocr_err:
                    logger.warning(f"OCR fallback could not run on page {page_num}: {ocr_err}")
            
            page_texts[page_num] = text
            
        doc.close()
        logger.info(f"Extracted {total_pages} pages from {path_str}. OCR needed on: {ocr_needed_pages}")
        return page_texts, ocr_needed_pages, total_pages
