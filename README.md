# AI Insurance Assistant — Document Pipeline & Chat Platform

A complete, production-grade AI platform for insurance policies. Features an intelligent 9-stage document ingestion pipeline and an integrated retrieval chat workspace. Built with **FastAPI**, **Pure React (JavaScript / JSX + Vanilla CSS)**, PyMuPDF, pdfplumber, local BGE-small embeddings, and **Chroma Cloud** vector storage.

---

## Key Features
- **Dual-Mode Workspace**:
  - **📄 Document Ingestion (Phase 1)**: Upload PDFs manually, select policy category (**Customer Insurance** or **Employee Insurance**), track 9 real-time pipeline stages, view extracted table/calculation counts, and inspect run history.
  - **💬 AI Insurance Chat (Phase 2 Preview)**: Grounded conversational workspace ready for semantic vector search and policy clause citations.
- **Pure React (No TypeScript)**: Lightweight, clean JavaScript React using Vite and responsive local CSS (no external CDNs).
- **Chroma Cloud Ready**: Supports Chroma Cloud (`api_key`, `tenant`, `database`) and remote self-hosted Chroma HTTP servers via `.env`.
- **Hierarchical Extraction & Chunking**: Preserves all 17 numbered sections, subsections (`11.1`, `14.1`), tables, calculations, and footnotes.
- **Evidence-Based Policy Status**: Preserves 105 literal disclaimers in employee insurance with `data_status: illustrative_unverified`.
- **Local Dense Embeddings**: `BAAI/bge-small-en-v1.5` generating 384-dimensional normalized vectors with zero external API calls.
- **100% Automated Test Suite**: 18 unit, negative, and end-to-end integration tests.

---

## Quickstart

### 1. Backend Setup & Run (Command Prompt / CMD)
```cmd
cd /d C:\Users\shivu\OneDrive\Desktop\Capstone_rag
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup & Run (Command Prompt / CMD)
```cmd
cd /d C:\Users\shivu\OneDrive\Desktop\Capstone_rag\frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

### 3. Run Automated Tests (CMD)
```cmd
cd /d C:\Users\shivu\OneDrive\Desktop\Capstone_rag
.venv\Scripts\python.exe -m pytest backend/tests -v
```

---

## Live Demonstration for Mentors
1. Choose **Customer Insurance** or **Employee Insurance** from the dropdown.
2. Select your policy PDF manually (`health_shield_basic.pdf`, `health_shield_gold.pdf`, `health_shield_premium.pdf`, or `executive_employee_insurance_plan.pdf`).
3. Click **Start Document Ingestion** to run the live 9-stage pipeline.
4. Explore the **AI Insurance Chat** tab to preview the Phase 2 conversational retrieval interface.
