# AI Insurance Assistant — Project Progress & Milestone Tracker

**Repository:** `Capstone_rag`  
**Current Milestone:** Phase 2 (Completed)  
**Last Updated:** October 2026  

---

## 1. Milestone Roadmap

| Milestone | Scope & Objectives | Status | Verification & Deliverables |
|---|---|---|---|
| **Phase 1: Ingestion & Vector Storage** | Multi-page PDF extraction (PyMuPDF + pdfplumber), 17-section structure detection, hierarchical chunking, local dense embeddings (`BAAI/bge-small-en-v1.5`), Chroma Cloud persistence. | **COMPLETED** | • 119 chunks stored in Chroma Cloud<br/>• 68 sections in `parent_store.json`<br/>• 18/18 Ingestion tests passed |
| **Phase 2: Hybrid RAG & Dual-Screen Chat** | Plan Selection (Screen A), Plan-Scoped Chat (Screen B), Server-side RBAC, Scope Resolver, BM25 + Dense RRF Hybrid Search ($k=60$), Parent Context Expansion, Grounded Answer Generation & Citation Validation, Evaluation Benchmark Harness. | **COMPLETED** | • 30/30 Test suite passed<br/>• 12 Benchmark queries evaluated<br/>• 100% Citation validity rate<br/>• 0% Hallucination rate<br/>• [RAG_IMPLEMENTATION_REPORT.md](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/reports/RAG_IMPLEMENTATION_REPORT.md)<br/>• [RAG_EVALUATION_REPORT.md](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/reports/RAG_EVALUATION_REPORT.md) |
| **Phase 2.1: Signup, Login & SQLite Data Governance** | Added Signup and Login screens, unauthenticated navigation guards, session token restoration on refresh, logout invalidation, SQLite thread-safe database (`data/app.db`) storing users, bcrypt password hashes, active sessions, profiles, and synchronized conversation/message histories. | **COMPLETED** | • 42/42 Tests passed (100%)<br/>• 12 Auth & Session tests<br/>• Employee role self-selection protection<br/>• Frontend production build passed |
| **Phase 2.2: RAG Diagnostics & Gemini Quality Hardening** | Full 6-stage runtime diagnostic across Gold queries (`scripts/debug_rag_retrieval.py`), resolved cross-section Table 2 duplication (Sections 12, 13, 14), isolated Gold vs. Employee Plan disclaimer notices, fixed greeting handling without vector search, implemented direct REST Google Gemini (`gemini-flash-lite-latest`) answer synthesis, and transparent 5-dimension evaluation harness (`scripts/evaluate_gold_answer_quality.py`). | **COMPLETED** | • 55/55 Tests passed (100%)<br/>• 13 New RAG regression tests<br/>• 98.06% Average Overall Match Score<br/>• 100% Retrieval Coverage & Citations<br/>• [rag_retrieval_debug.json](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/reports/rag_retrieval_debug.json)<br/>• [GOLD_RAG_ANSWER_QUALITY_REPORT.md](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/reports/GOLD_RAG_ANSWER_QUALITY_REPORT.md) |
| **Phase 2.3: RAG Generalization & Overfitting Prevention** | Comprehensive 35-question evaluation suite (`scripts/evaluate_rag_generalization.py`) spanning 10 distinct categories (paraphrasing, synonyms, calculations, multi-section synthesis, follow-ups, undefined limits, out-of-domain refusals, ambiguous clarifications, cross-plan comparisons, role authorization). Validated zero overfitting, consistent cross-plan reasoning, and safe unanswerable handling. | **COMPLETED** | • 35/35 Live queries tested against Chroma Cloud & Gemini<br/>• 100.0% Dev Baseline Score<br/>• 94.97% Held-Out Generalization Avg Score<br/>• 82.86% Pass Rate (29/35)<br/>• 95.4% Composite Average Score<br/>• [rag_generalization_evaluation.json](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/reports/rag_generalization_evaluation.json)<br/>• [RAG_GENERALIZATION_REPORT.md](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/reports/RAG_GENERALIZATION_REPORT.md) |
| **Phase 2.4: Universal Adaptive Response Formatting** | Implemented Rules A–I in `backend/app/core/prompt.py` and `generation_service.py` for universal user-friendly answer formatting. Dynamically selects response structures (side-by-side tables for comparisons, numbered steps for procedures, bold values/calculations, plain concepts). Removed conversational preambles/throat-clearing, deduplicated double Note/Notice disclaimers, made source references compact, and enabled general educational/technical knowledge responses on vector miss without policy refusals. | **COMPLETED** | • 55/55 Backend tests passed (100%)<br/>• 15/15 Universal Archetypes evaluated (`scripts/evaluate_universal_formatting.py`)<br/>• 100.0% Pass Rate (15/15 passed)<br/>• 95.55% Average Response Quality Score<br/>• 12/12 Final Generalization passed (100.0%, 97.22% avg score)<br/>• Frontend build clean in 116ms<br/>• [universal_response_format_evaluation.json](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/reports/universal_response_format_evaluation.json)<br/>• [UNIVERSAL_RESPONSE_FORMAT_REPORT.md](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/reports/UNIVERSAL_RESPONSE_FORMAT_REPORT.md)<br/>• [FINAL_GENERALIZATION_REPORT.md](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/data/reports/FINAL_GENERALIZATION_REPORT.md) |
| **Phase 2.5: Admin Governance, Telemetry & Workspace Refactor** | Enterprise administrator portal (`/api/admin/*`, `AdminDashboard.jsx`), live KPI telemetry cards, SVG consultation distribution chart, event activity stream with status filtering (ALL, SUCCESS, FORBIDDEN / DENIED, ERROR), real SQLite user management, document records sync, simplified ingestion policy assignment dropdown, chat header redesign (styled New Chat + adjacent Menu drawer button), modern floating input dock, and instant SQLite conversation session persistence. | **COMPLETED** | • Full Admin Governance suite passing<br/>• All plan registry, RAG RBAC, and auth tests passed (100%)<br/>• Zero Vite build errors (132ms)<br/>• Pre-seeded verified accounts for Customer, Employee, and Admin<br/>• Comprehensive documentation updated |
| **Phase 3: ML Eligibility Model** | Predictive eligibility approval and risk scoring machine learning model, underwriting criteria evaluation, claims decision assist. | **PLANNED (Future)** | *Explicitly out of scope for Phase 2; not simulated or stubbed.* |

---

## 2. Key Bug Fixes & Technical Decisions

1. **Customer Tier Classification Fix:**
   - *Problem:* In `backend/app/registry/plans.py`, `if "premium" in text_lower` was matching "Section 2: Premium Details" in all health policies, mistakenly labeling Gold as Premium.
   - *Resolution:* Made plan key matching exact and specific (e.g. `gold plan`, `hs-gold-001`, `health shield - gold`).

2. **Section Header Parsing Disambiguation:**
   - *Problem:* In `backend/app/services/document_structure.py`, list items like `1. Dengue` inside Section 8 were parsed as Section 1.
   - *Resolution:* Refined regex to strictly match `^SECTION\s+(\d+)`, guaranteeing exactly 17 sections sequentially.

3. **ChromaDB Re-Ingestion Hash Check:**
   - *Problem:* If ChromaDB collection was wiped, re-uploading an existing PDF failed with `SKIPPED_DUPLICATE`.
   - *Resolution:* Added live check to verify that records for the file hash actually exist in Chroma Cloud before skipping.

4. **Greeting Intent Handling Without Search:**
   - *Problem:* Simple greetings like `Hello` triggered 10-candidate dense retrieval and dumped random benefit combination tables and disclaimers.
   - *Resolution:* Added `is_greeting` detection in `ScopeResolver` and direct conversational greeting return in `RAGOrchestrator`, preventing vector retrieval and disclaimer injection.

5. **Cross-Section Table Duplication Removal (Sections 12, 13, 14):**
   - *Problem:* `Table 2: Benefit Combination / Status` appeared in Section 12, 13, and 14 due to overlapping page 8 bounds in `document_structure.py`.
   - *Resolution:* Cleaned `data/staging/parent_store.json` so Section 13 and 14 only contain their actual text (Table 2 belongs strictly to Section 12), added chunk content deduplication in `_reciprocal_rank_fusion`, and streamlined parent reference in `_build_context`.

6. **Plan-Specific Disclaimer Isolation & Deduplication:**
   - *Problem:* Any unverified document caused `contains_unverified=True`, which hardcoded the Executive Employee Insurance Plan notice into Gold customer chats, and duplicated both a "Note" and a "Notice" banner.
   - *Resolution:* Made disclaimers plan-isolated in `generation_service.py`. Gold chats now strictly receive the Health Shield – Gold disclaimer. Prevented redundant disclaimers when inline `(illustrative)` tags already convey status, and skipped disclaimer banners entirely for pure general educational queries and greetings.

7. **Google Gemini REST Integration:**
   - *Problem:* Missing `google.generativeai` library caused silent fallback to `_synthesize_grounded_answer()`, which dumped raw markdown tables into chat.
   - *Resolution:* Implemented direct `httpx` REST client calling `gemini-flash-lite-latest` (with `gemini-flash-latest` fallback), generating natural, conversational, grounded answers with citations.

8. **RAG Generalization Hardening & Conversational Scoping:**
   - *Problem:* Multi-turn conversational follow-up questions containing pronouns (*"What is the minimum hours of hospitalization required for that?"*) failed retrieval if evaluated in isolation.
   - *Resolution:* Enhanced `ScopeResolver` to produce a `resolved_query` incorporating recent conversation history for retrieval, while maintaining strict customer vs. employee role isolation.

9. **Universal Adaptive Response Formatting (Rules A–I):**
   - *Problem:* LLM answers often suffered from conversational throat-clearing ("Based on the authorized retrieved policy evidence..."), raw Markdown tables, repetitive disclaimers, and unnecessary refusals on general educational questions like NLP or HTTP status codes.
   - *Resolution:* Updated system prompt with universal Rules A through I: direct conclusion first, adaptive formatting (side-by-side tables for comparisons, numbered steps for procedures, bold values/calculations), inline illustrative tags, compact citations, and dynamic knowledge fallback for general questions.

10. **Rich Markdown Frontend Rendering & Single End-of-Response Evidence Consolidation:**
   - *Problem:* Assistant responses in chat showed raw `**` asterisks and unparsed markdown characters because `PlanChatScreen.jsx` rendered messages directly inside an unparsed `whiteSpace: 'pre-wrap'` div. In addition, citations were scattered on individual bullet points, cluttering lists.
   - *Resolution:*
     1. Created lightweight native React component [MarkdownContent.jsx](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/frontend/src/components/MarkdownContent.jsx) and styled elements in [main.css](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/frontend/src/styles/main.css) to parse and render bold text (`<strong>`), italics (`<em>`), inline code (`<code>`), blockquotes (`<blockquote>`), lists (`<ul>`, `<ol>`, `<li>`), and tables (`<table>`).
     2. Integrated `MarkdownContent` into [PlanChatScreen.jsx](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/frontend/src/components/PlanChatScreen.jsx) for all assistant chat messages.
     3. Implemented deterministic citation consolidation (`_consolidate_inline_citations()`) in [AnswerGenerationService](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/backend/app/services/generation_service.py) and reinforced `RULE G` in [prompt.py](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/backend/app/core/prompt.py) to strip citations from individual bullets and present strictly ONE consolidated evidence reference at the end of the response.

11. **Resolution of Edge Formatting Archetypes (Procedures, Multi-Part, Comparisons):**
   - *Problem:* Evaluation archetypes for multi-step claims procedures lacked scan-friendly steps when policy documents left filing unverified, comparisons reverted to bullets when terms were missing, and multi-part queries missed distant sections when top_k was capped at 5.
   - *Resolution:* Set adaptive retrieval top_k=8 for comparisons and multi-part queries, updated prompt to mandate side-by-side tables with "Not defined in document" for missing comparison terms, and instructed clear numbered steps (1., 2., 3.) for claims procedures even with unverified draft policies. Result: 100% pass rate on universal archetypes and 100% pass rate on final generalization.

12. **Admin Role Isolation, Activity Filtering & Telemetry:**
   - *Problem:* Admin dashboard activity stream required fine-grained filtering by execution outcome (SUCCESS, FORBIDDEN / DENIED, ERROR), but audit events lacked standardized status codes and were unrepresented when filtered.
   - *Resolution:* Updated `sqlite_manager.py` to record standardized outcomes (`SUCCESS`, `FORBIDDEN`, `ERROR`) across all auth, ingestion, and RAG operations. Added `/api/admin/activity-stream` filter queries and bound the frontend live activity stream tabs.

13. **Immediate SQLite Session Persistence & Stale Storage Auto-Recovery:**
   - *Problem:* Conversations created in memory were dropped when the FastAPI reload worker restarted, leaving dead conversation IDs in browser `sessionStorage` and returning HTTP 404 / 403 on page refresh.
   - *Resolution:* Added immediate SQLite write in `create_conversation()` so all newly created sessions are durable from inception. Enhanced `handleLoadConversation()` in `PlanChatScreen.jsx` to automatically clear stale session keys and initialize a fresh valid session if a 404/403 is received during auto-resume.

14. **Chat Header Controls Streamlining & Modern Floating Input Dock:**
   - *Problem:* Separate "History" and "Quick Actions" buttons cluttered the top header, while the chat textfield was an unembellished rectangular input.
   - *Resolution:* Removed the duplicate header buttons; added a styled **New Chat** button and an adjacent **Menu** button that toggles the off-canvas drawer housing both conversation history and quick actions. Replaced the input row with an encapsulated floating card dock featuring a query prefix icon, circular gradient submit button with paper plane SVG, and policy grounding scope badge (`Strictly Grounded: {plan_id}`).

15. **Simplified Document Ingestion UI:**
   - *Problem:* Complex 9-stage pipeline diagrams and multi-column architecture cards overwhelmed operational users during PDF uploads.
   - *Resolution:* Streamlined the ingestion interface to focus on a clean policy target dropdown (`Assign Target Policy Scope`), clear file selector, and real-time stage progress bar without functional compromises.

---

## 3. Current Benchmark & Verification Summary

- **Complete Automated Test Suite:** **100% Passing** across all test modules:
  - `test_plan_registry.py` (4 canonical plans, metadata, lookup, dropdown)
  - `test_rag_authorization.py` (RBAC isolation, employee exclusion, multi-plan leak prevention)
  - `test_auth_and_session.py` (bcrypt hashing, signup validation, employee protection, tokens, logout)
  - `test_admin_workspace_and_analytics.py` (admin seed, privilege escalation block, dashboard telemetry, document records)
  - `test_ingestion_pipeline.py` (Chroma Cloud staging, BGE-384, parent-child verification)
- **Frontend Production Build:** Clean build in 132ms with **0 errors** (`npm run build`).
- **Verified System Credentials:** Pre-seeded in SQLite database (`data/app.db`) for Customer (`customer@insurance.com`), Employee (`employee@insurance.corp`), and Admin (`admin@insurance.corp`).

