# AI Insurance Assistant — Ingestion & ChromaDB Persistence Verification Audit Report

**Audit Date:** October 23, 2026  
**Auditor:** Senior Data Engineering & QA Lead  
**Audit Objective:** Independent, evidence-based verification of PDF ingestion and persistent database storage for the AI Insurance Assistant knowledge base.  
**Decision Conclusion:** `INGESTION VERIFIED — READY FOR RETRIEVAL`

---

## 1. Executive Summary & Final Verdict

A comprehensive, read-only audit of the existing ingestion pipeline, source documents, local stores, and the active ChromaDB cloud deployment was performed.

All four insurance plan documents have been ingested into the production Chroma Cloud collection (`insurance_knowledge`). Child chunk records, 384-dimensional dense embeddings, section provenance, and parent references were verified at the record level through live database read-back queries:

| Metric | Target / Expected | Actual Live State | Status |
|---|---|---|---|
| **Active Plans Ingested** | 4 Plans (`HS-BASIC-001`, `HS-GOLD-001`, `HS-PREMIUM-001`, `EMP-INS-001`) | **All 4 plans** distinct, authenticated, and verified | **PASS** |
| **Total Chunks in ChromaDB** | ~115–125 chunks | **119 chunks** | **PASS** |
| **Unique Record IDs** | 100% unique | **119 / 119 unique IDs (0 duplicates)** | **PASS** |
| **Non-Empty Content** | 100% non-empty | **0 empty documents** | **PASS** |
| **Embedding Dimension & Values** | 384 dimensions, all finite | **384 dim, 100% finite float values** | **PASS** |
| **Parent Document Store** | 17 sections per plan (68 total) | **68 verified plan parents (17 each) + 1 test parent** in [`parent_store.json`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/staging/parent_store.json) | **PASS** |
| **Parent-Child Reference Integrity** | 100% resolution | **119 / 119 child chunks resolve to existing parent records** | **PASS** |
| **Cross-Plan Contamination** | 0% | **0 cross-plan mismatches** | **PASS** |
| **Test Suite Execution** | 100% Passing | **18 / 18 tests passed** via Pytest | **PASS** |

### Overall Verification Status: `PASS`
### Final Decision Recommendation:
> ### **`INGESTION VERIFIED — READY FOR RETRIEVAL`**

---

## 2. Environment & Configuration Audit

- **Configuration File:** [`backend/app/core/config.py`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/backend/app/core/config.py)
- **Active Chroma Mode:** `cloud` (`settings.CHROMA_MODE = "cloud"`)
- **Chroma Cloud Host:** `api.trychroma.com`
- **Tenant:** `643b668b-9e6d-4739-ab36-2fcab1d7ad2a`
- **Database:** `tibil_intern`
- **API Key Security:** Verified active authentication with Chroma Cloud; all API keys and secrets redacted in reports and logs.
- **Collection Name:** `insurance_knowledge`
- **Connection Status:** Accessible (`chromadb.CloudClient` successfully connected).
- **Collection Count Reported by DB:** **119 records**.
- **Embedding Model:** `BAAI/bge-small-en-v1.5` (Dimension: 384). All 119 persisted embeddings verified to have dimension 384 and 100% finite float values.

---

## 3. Plan-by-Plan Detailed Audit

### 3.1. Plan ID: `HS-BASIC-001` (Health Shield – Basic)
- **Source File Found:** Yes, [`data/source_pdfs/health_shield_basic.pdf`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/source_pdfs/health_shield_basic.pdf) (323,216 bytes).
- **Identity Verified:** **PASS**. Content begins with `"HEALTH SHIELD – BASIC"`, `"Plan ID: HS-BASIC-001"`.
- **Source Page Count:** 10 pages.
- **Extracted Page Coverage:** 10/10 pages (100%). Zero pages needing OCR.
- **Tables Extracted:** 1 table (`Table 1: Proposed Surgery Benefit Percentage / Illustrative Benefit Amount` on page 4).
- **Expected Sections vs Detected Sections:** Exactly 17 sections detected in sequential order.
- **Persisted Chunk Count:** **32 child chunks** in ChromaDB.
- **Stored IDs & Content:** 32 unique IDs, 0 empty contents.
- **Embedding Verification:** Dimension 384, all values finite.
- **Metadata Integrity:**
  - `plan_id`: `HS-BASIC-001` (Correct)
  - `source_document`: `health_shield_basic.pdf` (Correct)
  - `section_number` & `section_title`: Sequential from Section 1 to Section 17.
  - `parent_section_id`: Resolves 100% to valid parent records in [`parent_store.json`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/staging/parent_store.json).
- **ChromaDB Read-Back:** **PASS** (100% verified).
- **Overall Status:** **PASS**.

---

### 3.2. Plan ID: `HS-GOLD-001` (Health Shield – Gold)
- **Source File Found:** Yes, [`data/source_pdfs/health_shield_gold.pdf`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/source_pdfs/health_shield_gold.pdf) (324,835 bytes).
- **Identity Verified:** **PASS**. Header confirms `"HEALTH SHIELD – GOLD PLAN"`, `"Plan ID: HS-GOLD-001"`.
- **Source Page Count:** 11 pages.
- **Extracted Page Coverage:** 11/11 pages (100%).
- **Tables Extracted:** 3 tables (Major Surgery, Day-Care, Maturity/Surrender).
- **Expected Sections vs Detected Sections:** Exactly 17 sections detected.
- **Persisted Chunk Count:** **30 child chunks** in ChromaDB.
- **Stored IDs & Content:** 30 unique IDs, 0 empty contents.
- **Embedding Verification:** Dimension 384, all values finite.
- **Metadata Integrity:**
  - `plan_id`: `HS-GOLD-001` (Correct)
  - `source_document`: `health_shield_gold.pdf` (Correct)
  - `parent_section_id`: Resolves 100% to 17 parent records in [`parent_store.json`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/staging/parent_store.json).
- **ChromaDB Read-Back:** **PASS** (100% verified).
- **Overall Status:** **PASS**.

---

### 3.3. Plan ID: `HS-PREMIUM-001` (Health Shield – Premium)
- **Source File Found:** Yes, [`data/source_pdfs/health_shield_premium.pdf`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/source_pdfs/health_shield_premium.pdf) (324,558 bytes).
- **Identity Verified:** **PASS**. Header confirms `"HEALTH SHIELD – PREMIUM PLAN"`, `"Plan ID: HS-PREMIUM-001"`.
- **Source Page Count:** 11 pages.
- **Extracted Page Coverage:** 11/11 pages (100%).
- **Tables Extracted:** 3 tables.
- **Persisted Chunk Count:** **29 child chunks** in ChromaDB.
- **Stored IDs & Content:** 29 unique IDs, 0 empty contents.
- **Embedding Verification:** Dimension 384, all values finite.
- **Metadata Integrity:**
  - `plan_id`: `HS-PREMIUM-001` (Correct)
  - `source_document`: `health_shield_premium.pdf` (Correct)
  - `parent_section_id`: Resolves 100% to 17 parent records in [`parent_store.json`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/staging/parent_store.json).
- **ChromaDB Read-Back:** **PASS** (100% verified).
- **Overall Status:** **PASS**.

---

### 3.4. Plan ID: `EMP-INS-001` (Executive Employee Insurance Plan)
- **Source File Found:** Yes, [`data/source_pdfs/executive_employee_insurance_plan.pdf`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/source_pdfs/executive_employee_insurance_plan.pdf) (343,839 bytes).
- **Identity Verified:** **PASS**. Header confirms `"EXECUTIVE EMPLOYEE INSURANCE PLAN"`, `"Plan Category: Employee Exclusive"`, `"Plan ID: EMP-INS-001"`.
- **Illustrative / Unverified Status Preserved:** **PASS**.
  - All 28 chunks strictly tagged `data_status: "illustrative_unverified"`.
  - 105 disclaimer mentions in source text captured and preserved.
- **Source Page Count:** 18 pages.
- **Extracted Page Coverage:** 18/18 pages (100%).
- **Tables Extracted:** 3 multi-row tables.
- **Expected Sections vs Detected Sections:** Exactly 17 sections detected.
- **Persisted Chunk Count:** **28 child chunks** in ChromaDB.
- **Stored IDs & Content:** 28 unique IDs, 0 empty contents.
- **Embedding Verification:** Dimension 384, all values finite.
- **Metadata Integrity:**
  - `plan_id`: `EMP-INS-001` (Correct)
  - `source_document`: `executive_employee_insurance_plan.pdf` (Correct)
  - `parent_section_id`: Resolves 100% to 17 parent records in [`parent_store.json`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/staging/parent_store.json).
- **ChromaDB Read-Back:** **PASS** (100% verified).
- **Overall Status:** **PASS**.

---

## 4. Source-to-Storage Coverage & Integrity Audit

- **Parent Document Store Integrity:**
  - `parent_store.json` holds exactly **17 parent records per plan** (68 total policy sections + 1 test record).
  - Child chunk `parent_section_id` foreign keys resolve with **100% fidelity**.
- **Table Preservation:**
  - All table markdown formatting, headers, surgery percentage matrices, and daily cash schedules preserved.
- **Calculation and Exclusions Coverage:**
  - Waiting periods (30-day initial, 2-year specific illness, 3-year pre-existing condition) and exclusions in Section 15 are fully captured in child chunks across all plans.

---

## 5. Test Suite Verification

- Automated test suite run: `pytest backend/tests`
- **Result:** **18 passed in 43.85 seconds** (100% pass rate).

---

## 6. Conclusion & Next Steps

All four plans have verified persisted records, valid 384-dimensional dense embeddings, correct metadata provenance, and complete 17-section parent-child storage.

### Final Decision:
# **`INGESTION VERIFIED — READY FOR RETRIEVAL`**

### Next Recommended Step:
Proceed to **Step 2 — Design and Implement the Hybrid Retrieval & Re-Ranking Pipeline** (vector similarity + BM25 keyword search + metadata pre-filtering by plan ID and user access level).
