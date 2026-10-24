import os
import re
import pymupdf

pdf_dir = "data/source_pdfs"
files = [
    "health_shield_basic.pdf",
    "health_shield_gold.pdf",
    "health_shield_premium.pdf",
    "executive_employee_insurance_plan.pdf"
]

print("=== PHASE 1: PDF WORKSPACE INSPECTION ===")
for fname in files:
    fpath = os.path.join(pdf_dir, fname)
    if not os.path.exists(fpath):
        print(f"[-] MISSING: {fname}")
        continue
    
    doc = pymupdf.open(fpath)
    page_count = len(doc)
    print(f"\n[+] File: {fname}")
    print(f"    Total Pages: {page_count}")
    
    # Extract text from first 2 pages
    p1_text = doc[0].get_text() if page_count > 0 else ""
    p2_text = doc[1].get_text() if page_count > 1 else ""
    first_lines = [l.strip() for l in p1_text.splitlines() if l.strip()][:6]
    print(f"    First Page Title/Header: {' | '.join(first_lines)}")
    
    # Check 17 section headings across document
    full_text = ""
    for pno in range(page_count):
        full_text += f"\n--- Page {pno+1} ---\n" + doc[pno].get_text()
        
    detected_sections = []
    for s_num in range(1, 18):
        # Look for e.g. "1. Purpose" or "Section 1" or "1."
        pattern = rf"(?:Section\s+{s_num}[:\.\s]|(?:\n|^)\s*{s_num}\.\s+([^\n]+))"
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            heading = match.group(0).strip().replace('\n', ' ')
            detected_sections.append((s_num, heading[:50]))
            
    print(f"    Sections detected ({len(detected_sections)}/17):")
    for s_num, h_text in detected_sections:
        print(f"      Sec {s_num}: {h_text}")
        
    # Check for illustrative / unverified keywords
    unverified_count = len(re.findall(r"(?:not\s+verified|not\s+defined|illustrative)", full_text, re.IGNORECASE))
    print(f"    'Illustrative / Not Verified / Not Defined' occurrences: {unverified_count}")
    doc.close()

print("\n=== INSPECTION SCRIPT FINISHED ===")
