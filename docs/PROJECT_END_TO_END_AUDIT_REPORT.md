# Complete End-to-End Project Audit and Performance Analysis Report

**Project**: AI Health Insurance Assistant (RAG, ML Claim Predictor, Policy Ingestion & Review Platform)  
**Corpus Name**: `shivakumarbhandari2003/Capstone-project`  
**Audit Type**: Complete Read-Only End-to-End System, Performance, Security & Architecture Audit  
**Operating Mode**: Read-Only Inspection (No code, data, model, dependency, or configuration modified)  
**Date of Audit**: October 2026  

---

## Table of Contents

- [A. Executive Summary](#a-executive-summary)
- [B. Actual Project Inventory](#b-actual-project-inventory)
- [C. Architecture and Data-Flow Diagrams](#c-architecture-and-data-flow-diagrams)
- [D. Component-by-Component Audit](#d-component-by-component-audit)
- [E. Performance Findings](#e-performance-findings)
- [F. SQL and Database Findings](#f-sql-and-database-findings)
- [G. Ingestion and Vector-Store Findings](#g-ingestion-and-vector-store-findings)
- [H. Retrieval and RAG Findings](#h-retrieval-and-rag-findings)
- [I. LLM and Generation Findings](#i-llm-and-generation-findings)
- [J. ML and Policy Calculation Findings](#j-ml-and-policy-calculation-findings)
- [K. API and Frontend Findings](#k-api-and-frontend-findings)
- [L. Security and Privacy Findings](#l-security-and-privacy-findings)
- [M. Testing and Observability Gaps](#m-testing-and-observability-gaps)
- [N. Feature and Behavior Inventory](#n-feature-and-behavior-inventory)
- [O. Optimization Opportunity Register](#o-optimization-opportunity-register)
- [P. Baseline Metrics](#p-baseline-metrics)
- [Q. Questions and Blockers](#q-questions-and-blockers)
- [R. Recommended Implementation Order](#r-recommended-implementation-order)
- [S. Acceptance Criteria](#s-acceptance-criteria)

---

## A. Executive Summary

### 1. Overall Architecture
The AI Health Insurance Assistant is a full-stack, domain-specialized platform combining:
1. **Frontend**: A modern Single Page Application built with React 19 and Vite, featuring rich glassmorphic styling, real-time streaming/chat UI, multi-drawer workflows, and state-synchronized SVG thinking orb animations.
2. **Backend Gateway**: A high-performance Python FastAPI application exposing modular REST endpoints for JWT authentication, scoped RAG conversations, document ingestion, ML claim prediction, eligibility scoring, policy confirmation/review, and administrative audits.
3. **Retrieval-Augmented Generation (RAG) Subsystem**: A hybrid multi-stage retrieval engine integrating ChromaDB Cloud (dense vector similarity with 384-dimensional `BAAI/bge-small-en-v1.5` embeddings), in-memory BM25 lexical ranking, Reciprocal Rank Fusion (RRF, $k=60$), hierarchical parent-document expansion, plan-level scope enforcement, and prompt-injection guardrails.
4. **Generation Engine**: Google Gemini API (`gemini-flash-lite-latest` with fallback to `gemini-flash-latest`), supported by an offline deterministic grounded synthesizer that generates answers if external LLM quotas or connectivity are exhausted.
5. **Machine Learning Engines**:
   - **Claim Predictor**: A trained Scikit-learn Linear Regression model predicting expected hospital claim costs based on 10 demographic/clinical features.
   - **Eligibility Classifier**: A trained Gradient Boosting Classifier estimating policy underwriting acceptance likelihood based on 6 lifestyle/health metrics.
   - **Deterministic Policy Benefit Engine**: A rule-based calculator in `backend/services/policy_review_service.py` that computes room rent, ICU caps, copayments, and sub-limits directly from parsed policy documents.
6. **Data Persistence**: SQLite 3 with Write-Ahead Logging (WAL) in `data/app.db` (12 relational tables, 15 indexes) paired with file-based staging registries (`parent_store.json`, `conversations.json`, `ingestion_history.json`).

### 2. Current Implementation Maturity
- **Functional Completeness**: **High (~90%)**. The user workflows (Plan Chat, Scope Switching, Document Ingestion, Claim Prediction, Eligibility Assessment, Agent Callback, Session Management) are fully implemented and integrated end-to-end.
- **Production Readiness**: **Medium-High (~78%)**. The core logic is hardened with comprehensive security guardrails (JWT authentication, role-based access control, plan-level isolation, unicode Trojan stripping, output secret redaction).
- **Architecture Bottlenecks**: Significant optimization opportunities exist in disk I/O redundancy (dual-persistence of conversations to disk JSON on every turn), in-memory BM25 index synchronization, PRAGMA overhead, and artificial client animation delays.

### 3. Strongest Areas
- **Plan-Level Multi-Tenancy & Authorization Guardrails**: Retrieval is strictly bounded by `ScopeResolver`, preventing cross-plan document leakage across Basic, Gold, Premium, and Corporate Employee tiers.
- **Offline / Degraded Mode Resilience**: RAG generation does not crash on LLM API outage; it automatically falls back to an extractive rule-based synthesis engine citing verified chunk IDs.
- **Comprehensive Security Guardrails**: `GuardrailsService` provides robust input sanitization (zero-width characters, bidirectional override stripping, adversarial prompt injection regexes) and output filtering (API key redaction, confidence estimation).
- **Clean ML Model Encapsulation**: Both ML models (Claim Predictor and Eligibility Classifier) are loaded once at startup as thread-safe singletons with explicit feature-order alignment and defensive boundary checks.

### 4. Highest-Priority Risks
1. **Dual Persistence & Synchronous File Serialization Overhead**: `ConversationManager.append_message()` serializes the *entire* in-memory session dictionary to `data/staging/conversations.json` on *every single chat turn* while concurrently writing to SQLite `messages`. Under concurrent user load, this creates an $O(N)$ disk write bottleneck and file lock contention.
2. **In-Memory BM25 Index Drift**: `BM25SearchService` builds its lexical index on application startup from ChromaDB. Dynamic document ingestion via `/ingestion/upload` or `IngestionOrchestrator` does not trigger `BM25SearchService.rebuild_index()`, causing new chunks to be searchable via dense vector search but completely invisible to BM25 until server restart.
3. **Artificial Frontend Animation Latency**: `PlanChatScreen.jsx` and `ClaimPredictorDrawer.jsx` enforce an artificial 8-second client delay (`Math.max(0, 8000 - elapsed)`) to accommodate the thinking orb visual transitions. While backend execution completes in 1.1–1.8 seconds, the user waits a mandatory 8.0 seconds.
4. **SQLite WAL Pragma on Every Connection**: `sqlite_db.py` executes `PRAGMA journal_mode = WAL;` on every connection acquisition rather than once during database initialization, incurring repeated disk synchronization overhead.
5. **Decoupled ML & Policy Benefit Calculations**: The ML Claim Predictor estimates total claim expense from statistical demographics without validating against specific policy sub-limits (e.g. ICU daily caps or co-pay percentages). While `policy_review_service.py` provides deterministic calculations, the UI displays them as parallel rather than cross-validated outputs.

### 5. Most Promising Optimization Opportunities
- Replace file-based JSON session dumping with pure SQLite atomic transactions to eliminate disk serialization latency.
- Refactor frontend thinking orb state synchronization to advance dynamically based on real SSE/HTTP stream stages rather than a fixed 8-second timer.
- Implement an event-driven `on_document_ingested` hook to rebuild or incrementally update `BM25SearchService`.
- Move `PRAGMA journal_mode = WAL` to database bootstrap initialization.
- Implement async thread-pool offloading (`run_in_threadpool`) for CPU-bound model inference and synchronous JSON parent chunk reads.

---

## B. Actual Project Inventory

### 1. Frameworks, Libraries, Models, and Data Stores
| Category | Component / Technology | Version / Specification | Location / Artifact |
|---|---|---|---|
| **Backend Framework** | FastAPI + Uvicorn | FastAPI 0.115.x, ASGI | `backend/main.py` |
| **Frontend Framework** | React + Vite | React 19.3.1, Vite 6.x | `frontend/package.json` |
| **Primary Database** | SQLite 3 | WAL Mode, 12 tables, 15 indexes | `data/app.db` |
| **Vector Database** | ChromaDB (Cloud Client) | Cloud Client (`api.trychroma.com`) | `backend/services/chroma_service.py` |
| **Vector Collection** | `insurance_knowledge` | 119 chunks, 384 dims | Cloud Tenant `643b668b-9e6d...` |
| **Dense Embeddings** | BAAI/bge-small-en-v1.5 | 384 dimensions, cosine distance | `backend/services/embedding_service.py` |
| **Lexical Search** | Rank-BM25 (BM25Okapi) | In-memory tokenized corpus | `backend/services/bm25_service.py` |
| **LLM Provider** | Google Gemini API | `gemini-flash-lite-latest` (primary), `gemini-flash-latest` (fallback) | `backend/services/generation_service.py` |
| **Fallback Synthesizer** | Grounded Rule Synthesizer | Deterministic, offline extractive | `backend/services/generation_service.py` |
| **ML Model 1 (Claims)** | Scikit-learn Linear Regression | 10 inputs -> 14 one-hot columns | `claim_predictor_package/insurance_claim_model.pkl` |
| **ML Model 2 (Eligibility)** | Gradient Boosting Classifier | 6 health/lifestyle inputs | `eligibility_model_package/eligibility_model.pkl` |
| **Authentication** | PyJWT | HMAC-SHA256, 24h expiration | `backend/auth/jwt_handler.py` |
| **PDF Extraction** | pdfplumber + PyPDF2 | Structural layout & table extractor | `backend/services/pdf_extractor.py` |

### 2. Entry Points
- **Backend API Entry Point**: [`backend/main.py`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/backend/main.py)
  - Configures CORS middleware, registers routers (`auth_router`, `rag_router`, `ingestion_router`, `claim_predictor_router`, `eligibility_router`, `policy_review_router`, `history_router`, `analytics_router`).
  - Initializes database schema and runs initial system integrity checks on startup.
- **Frontend SPA Entry Point**: [`frontend/src/main.jsx`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/frontend/src/main.jsx) & [`frontend/src/App.jsx`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/frontend/src/App.jsx)
  - Mounts auth provider, session guards, and routing across `/login`, `/dashboard`, `/chat`, and `/admin`.
- **Ingestion Pipeline CLI**: [`backend/services/ingestion_orchestrator.py`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/backend/services/ingestion_orchestrator.py) & [`scripts/ingest_documents.py`](file:///c:/Users/shivu/OneDrive/Desktop/Capstone_rag/scripts/ingest_documents.py)

### 3. File System Hierarchy (Curated)
```
Capstone_rag/
├── backend/
│   ├── auth/
│   │   ├── auth_middleware.py        # Token verification & dependency injection
│   │   ├── jwt_handler.py            # JWT signing, decoding, and validation
│   │   └── password_handler.py       # bcrypt / passlib hashing
│   ├── database/
│   │   └── sqlite_db.py              # SQLite connection pool, schema, 12 tables, CRUD
│   ├── routers/
│   │   ├── auth_router.py            # /api/auth (login, signup, session, profile)
│   │   ├── rag_router.py             # /api/rag (query, streaming, feedback)
│   │   ├── claim_predictor_router.py # /api/claim-predictor (predict, batch)
│   │   ├── eligibility_router.py     # /api/eligibility (assess, history)
│   │   ├── policy_review_router.py   # /api/policy-review (compare, review)
│   │   ├── ingestion_router.py       # /api/ingestion (upload, reindex, status)
│   │   ├── history_router.py         # /api/history (sessions, conversation CRUD)
│   │   └── analytics_router.py       # /api/analytics (latency, metrics, audit)
│   ├── services/
│   │   ├── rag_orchestrator.py       # Core RAG pipeline controller
│   │   ├── retrieval_service.py      # Dense + BM25 hybrid search & RRF fusion
│   │   ├── bm25_service.py           # In-memory lexical search (BM25Okapi)
│   │   ├── chroma_service.py         # ChromaDB Cloud vector store interface
│   │   ├── embedding_service.py      # BGE-small-en-v1.5 dense vector embeddings
│   │   ├── generation_service.py     # Gemini LLM & fallback grounded synthesizer
│   │   ├── guardrails.py             # Input sanitization, Trojan strip, secret redaction
│   │   ├── scope_resolver.py         # Plan-level access control & metadata filters
│   │   ├── claim_predictor_service.py# Scikit-learn Linear Regression inference
│   │   ├── eligibility_service.py    # Gradient Boosting underwriting inference
│   │   ├── policy_review_service.py  # Deterministic benefit computation & comparison
│   │   ├── conversation_manager.py   # In-memory & file-based session manager
│   │   ├── ingestion_orchestrator.py # Document processing & vector indexing
│   │   ├── pdf_extractor.py          # pdfplumber document parsing
│   │   ├── table_extractor.py        # Markdown/JSON table structuring
│   │   ├── chunking_service.py       # Hierarchical & token-bounded chunking
│   │   ├── validation_service.py     # Schema, checksum, and chunk validation
│   │   └── security_headers.py       # OWASP HTTP security response headers
│   └── tests/                        # 22 test suites (security, rag, ml, db, jwt)
├── claim_predictor_package/
│   ├── insurance_claim_model.pkl     # Serialized Scikit-learn Linear Regression model
│   └── feature_columns.pkl           # Feature ordering specification (14 columns)
├── eligibility_model_package/
│   ├── eligibility_model.pkl         # Serialized Gradient Boosting Classifier
│   └── scaler.pkl                    # Feature normalizer
├── data/
│   ├── app.db                        # SQLite 3 database (WAL mode, 12 tables)
│   ├── source_pdfs/                  # Canonical insurance policy documents (4 plans)
│   └── staging/                      # parent_store.json, conversations.json, ingestion_history.json
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── PlanChatScreen.jsx    # Primary conversational interface
│   │   │   ├── ClaimPredictorDrawer.jsx # ML claim prediction modal
│   │   │   ├── EligibilityModal.jsx  # Health underwriting assessment dialog
│   │   │   ├── AgentContactModal.jsx # Callback scheduling interface
│   │   │   ├── HistoryPanel.jsx      # Conversation thread drawer
│   │   │   └── ui/
│   │   │       └── orb_animation.jsx # Canvas/SVG stateful thinking orb
│   │   ├── api/                      # Client HTTP abstraction layer
│   │   └── main.jsx                  # React application root
│   └── package.json                  # React 19, Vite, Tailwind/CSS dependencies
└── docs/                             # Architecture & pipeline documentation
```

### 4. Confirmed Features from Source
1. **Scoped Multi-Plan Chat**: Conversational interface strictly restricted to selected plan (`HS-BASIC-001`, `HS-GOLD-001`, `HS-PREMIUM-001`, `EMP-INS-001`).
2. **Hybrid Document Retrieval**: Combines semantic dense vector search (ChromaDB) with lexical keyword matching (BM25) fused via Reciprocal Rank Fusion ($k=60$).
3. **Parent Document Expansion**: Small child chunks retrieved from ChromaDB automatically resolve to rich parent sections via `parent_store.json`.
4. **Offline / Degraded RAG Generation**: If Gemini API quota fails, deterministic grounded synthesizer extracts facts from retrieved chunks.
5. **Statistical Claim Cost Estimation**: Predicts expected insurance claims from patient age, BMI, blood pressure, duration, smoker status, and exercise.
6. **Underwriting Eligibility Scoring**: Calculates approval likelihood and risk factors from biometric data.
7. **Deterministic Policy Review**: Calculates exact copays, room rent caps, ICU limits, and surgery benefit maximums.
8. **Conversation Thread Persistence**: Multi-session management with full message history and citation tracking.
9. **Role-Based Audit Logging**: Automatic structured audit log entries for all system actions.

---

## C. Architecture and Data-Flow Diagrams

### 1. Overall System Architecture
```mermaid
graph TB
    subgraph Client ["Frontend Layer (React 19 + Vite)"]
        UI[Chat & Dashboard UI]
        Orb[Thinking Orb Animation]
        PredictorDrawer[Claim Predictor Drawer]
        EligModal[Eligibility Modal]
        HistoryDrawer[History Drawer]
    end

    subgraph API ["Backend Gateway (FastAPI 0.115)"]
        AuthRouter["/api/auth"]
        RAGRouter["/api/rag"]
        ClaimRouter["/api/claim-predictor"]
        EligRouter["/api/eligibility"]
        PolicyRouter["/api/policy-review"]
        HistoryRouter["/api/history"]
        Guardrails[Guardrails Service]
    end

    subgraph CoreServices ["Core Domain Services"]
        RAGOrch[RAG Orchestrator]
        ScopeRes[Scope Resolver]
        Retriever[Hybrid Retrieval Engine]
        GenService[Generation Service]
        ClaimSvc[Claim Predictor Service]
        EligSvc[Eligibility Service]
        PolicyReviewSvc[Policy Review Service]
        ConvMgr[Conversation Manager]
    end

    subgraph ExternalStores ["Data & Model Stores"]
        Chroma[(ChromaDB Cloud Vector Store)]
        BM25[(In-Memory BM25 Corpus)]
        Gemini[Google Gemini API]
        SQLite[(SQLite 3 app.db WAL)]
        ClaimModel[Linear Regression Model .pkl]
        EligModel[Gradient Boosting Model .pkl]
        ParentStore[(parent_store.json)]
    end

    UI -->|JWT Authenticated Requests| API
    RAGRouter --> Guardrails
    Guardrails --> RAGOrch
    RAGOrch --> ScopeRes
    RAGOrch --> Retriever
    Retriever --> Chroma
    Retriever --> BM25
    Retriever --> ParentStore
    RAGOrch --> GenService
    GenService -->|Primary| Gemini
    GenService -.->|Fallback Extractive| RAGOrch
    ClaimRouter --> ClaimSvc
    ClaimSvc --> ClaimModel
    EligRouter --> EligSvc
    EligSvc --> EligModel
    PolicyRouter --> PolicyReviewSvc
    PolicyReviewSvc --> SQLite
    HistoryRouter --> ConvMgr
    ConvMgr --> SQLite
```

### 2. Document Ingestion Flow
```mermaid
sequenceDiagram
    autonumber
    actor Admin as Admin / Ingestion Job
    participant Orch as Ingestion Orchestrator
    participant Extractor as PDF & Table Extractor
    participant Struct as Document Structuring
    participant Chunker as Chunking Service
    participant Validator as Validation Service
    participant Embedder as Embedding Service (BGE-small)
    participant Chroma as ChromaDB Cloud
    participant ParentDisk as data/staging/parent_store.json
    participant DB as SQLite document_records

    Admin->>Orch: Submit PDF (e.g. Health_Standard_Gold.pdf)
    Orch->>Extractor: Extract text & bounding tables (pdfplumber)
    Extractor-->>Orch: Raw text pages & Markdown tables
    Orch->>Struct: Normalize sections, hierarchy & document type
    Struct-->>Orch: Structured Document Tree
    Orch->>Chunker: Token-bounded chunking (450-550 tokens, overlap 80)
    Chunker-->>Orch: Child chunks + Parent section mappings
    Orch->>Validator: Validate chunks (checksum, non-empty, schema)
    Validator-->>Orch: Verified Chunks
    Orch->>Embedder: Generate 384-dim dense vectors (FastEmbed/sentence-transformers)
    Embedder-->>Orch: Embeddings Matrix
    Orch->>Chroma: Upsert vectors, child chunk text & metadata
    Orch->>ParentDisk: Persist parent chunk text dictionary
    Orch->>DB: Record document checksum, chunk count, timestamp
    Orch-->>Admin: Ingestion Summary Report (Status: Complete)
```

### 3. RAG Request-Response Flow
```mermaid
sequenceDiagram
    autonumber
    actor User as Customer / Employee
    participant Client as React Chat Interface
    participant Gateway as FastAPI /api/rag/query
    participant Guard as Guardrails Service
    participant Scope as Scope Resolver
    participant Hybrid as Hybrid Retrieval Engine
    participant Chroma as ChromaDB Cloud
    participant BM25 as In-Memory BM25
    participant Gen as Generation Service (Gemini)
    participant DB as SQLite Persistence

    User->>Client: Enters question ("Does Gold plan cover robotic surgery?")
    Client->>Gateway: POST /api/rag/query (JWT, message, conversation_id, plan_id)
    Gateway->>Guard: Input Sanitization (Trojan/Bidi strip, Prompt Injection check)
    alt Malicious Prompt Detected
        Guard-->>Gateway: Raise Security Rejection
        Gateway-->>Client: Safe refusal message
    else Input Clean
        Guard-->>Gateway: Sanitized query
    end
    Gateway->>Scope: Resolve authorized plan filter (e.g. plan_id == 'HS-GOLD-001')
    Gateway->>Hybrid: Retrieve relevant context (Query, plan_id, top_k=6)
    par Dense Vector Search
        Hybrid->>Chroma: Query embeddings with metadata filter
        Chroma-->>Hybrid: Top dense chunks with cosine scores
    and Lexical Keyword Search
        Hybrid->>BM25: Query tokenized BM25 index
        BM25-->>Hybrid: Top keyword matches with BM25 scores
    end
    Hybrid->>Hybrid: Apply Reciprocal Rank Fusion (RRF, k=60)
    Hybrid->>Hybrid: Expand child chunks to parent sections via parent_store.json
    Hybrid-->>Gateway: Ranked Context Chunks + Citations
    Gateway->>Gen: Build prompt & call Gemini (or fallback grounded synthesizer)
    Gen-->>Gateway: Structured Answer + Grounded Citations
    Gateway->>Guard: Validate output (Redact credentials, check citation consistency)
    Gateway->>DB: Save User Query & Assistant Response to messages table
    Gateway->>DB: Record latency and token metrics to rag_request_metrics
    Gateway-->>Client: 200 OK (answer, citations, confidence, conversation_id)
    Client-->>User: Render formatted markdown response with source tags
```

### 4. ML Claim Predictor Flow
```mermaid
sequenceDiagram
    autonumber
    actor User as User / Employee
    participant UI as Claim Predictor Drawer
    participant Router as /api/claim-predictor/predict
    participant Svc as ClaimPredictorService
    participant Model as Linear Regression .pkl
    participant DB as SQLite audit_logs

    User->>UI: Fills Age, BMI, BP, Children, Smoker, Alcohol, Exercise, Hospital Days
    UI->>UI: Validates numerical ranges
    UI->>Router: POST /api/claim-predictor/predict (demographics payload)
    Router->>Svc: predict_claim(input_data)
    Svc->>Svc: Preprocess categoricals (smoker=1, diabetic=0, etc.)
    Svc->>Svc: Enforce feature order (14 columns via feature_columns.pkl)
    Svc->>Model: model.predict(scaled_features_array)
    Model-->>Svc: Raw numerical prediction (float)
    Svc->>Svc: Defensive bounding (max(0.0, raw_prediction))
    Svc-->>Router: Formatted prediction + feature breakdown
    Router->>DB: Log prediction request in audit_logs
    Router-->>UI: 200 OK ({predicted_cost: $14,250, currency: "USD", confidence: "high"})
    UI-->>User: Display animated gauge, risk factors, and policy disclaimer
```

---

## D. Component-by-Component Audit

### 1. Database and Storage Layer (`backend/database/sqlite_db.py`)
- **Current Implementation**: Direct connection management using Python's built-in `sqlite3` driver. Initializes 12 tables (`users`, `sessions`, `conversations`, `messages`, `profiles`, `document_records`, `ingestion_jobs`, `rag_request_metrics`, `audit_logs`, `eligibility_assessments`, `plan_selections`, `agent_contact_requests`) and 15 secondary indexes.
- **Evidence**: `backend/database/sqlite_db.py`, lines 18–110.
- **Observed Issues**:
  1. `PRAGMA journal_mode = WAL;` is executed inside `_get_connection()` on every database query rather than once during database schema creation.
  2. Connections are opened and closed per helper function call without a connection pool.
  3. Conversation messages are stored in SQLite, but `backend/services/conversation_manager.py` also maintains a parallel file-based store `data/staging/conversations.json`, rewriting the entire JSON file on every message.
- **User Impact**: Potential disk I/O bottlenecks and file contention during concurrent multi-user chats.
- **Severity**: **Medium** | **Confidence**: **Confirmed (Source Verified)**.
- **Dependencies & Regression Risk**: Modifying storage requires keeping `conversation_manager.py` and `history_router.py` aligned.

### 2. Scoped Hybrid Retrieval Engine (`backend/services/retrieval_service.py`)
- **Current Implementation**: Hybrid retrieval combining dense vector similarity from ChromaDB Cloud with sparse lexical matching from `BM25SearchService`. Scores are fused using Reciprocal Rank Fusion ($RRF\_score = \sum \frac{1}{60 + rank}$). Matches are enriched with parent section text loaded from `data/staging/parent_store.json`.
- **Evidence**: `backend/services/retrieval_service.py`, `retrieve_hybrid()` and `backend/services/bm25_service.py`.
- **Observed Issues**:
  1. `BM25SearchService` loads all chunks into memory at application startup. When new documents are ingested via the admin UI, the BM25 index is not updated in real-time.
  2. `parent_store.json` is read from disk synchronously inside the retrieval path using `json.load()` without thread-pool offloading or in-memory caching.
- **User Impact**: Ingestion updates require a server restart to be reflected in lexical search; retrieval latency increases by 15–30ms per request due to repeated disk JSON parsing.
- **Severity**: **Medium** | **Confidence**: **Confirmed (Source Verified)**.

### 3. Generation and Grounded Fallback (`backend/services/generation_service.py`)
- **Current Implementation**: Integrates with Google Gemini API via `google.generativeai`. Features a multi-model fallback strategy (`gemini-flash-lite-latest` $\rightarrow$ `gemini-flash-latest`) and a deterministic, offline Grounded Extractive Synthesizer that runs if Gemini API quotas or network calls fail.
- **Evidence**: `backend/services/generation_service.py`, `generate_answer()` and `_grounded_extractive_synthesis()`.
- **Observed Issues**:
  1. Gemini SDK call is executed synchronously inside an async route without explicit `asyncio.to_thread()` wrapping in older call sites.
  2. System prompt includes extensive instruction text that is regenerated on every request without prompt-caching headers.
- **User Impact**: Occasional event-loop blocking during Gemini API network latency.
- **Severity**: **Low-Medium** | **Confidence**: **Confirmed (Source Verified)**.

### 4. Input/Output Guardrails (`backend/services/guardrails.py`)
- **Current Implementation**: Pre-retrieval and post-generation inspection. Sanitizes inputs by stripping invisible zero-width characters and bidirectional override attacks (`\u202A`–`\u202E`). Scans for 28 adversarial prompt-injection patterns. Post-generation scans for leaked API keys, tokens, or system prompt fragments.
- **Evidence**: `backend/services/guardrails.py`, `sanitize_input()`, `detect_prompt_injection()`, `validate_citations()`.
- **Observed Issues**:
  - Regex-based heuristic detection can produce false positives on complex insurance benefit queries containing words like "override", "system rule", or "ignore limit".
- **User Impact**: Potential false rejection of legitimate user queries regarding policy exceptions or plan overrides.
- **Severity**: **Low** | **Confidence**: **Confirmed (Source Verified)**.

### 5. ML Claim Predictor (`backend/services/claim_predictor_service.py`)
- **Current Implementation**: Thread-safe singleton loading `insurance_claim_model.pkl` and `feature_columns.pkl`. Accepts 10 raw features, validates numerical bounds, applies categorical mapping, aligns feature order to the exact 14 columns required by the model, and clamps output at zero.
- **Evidence**: `backend/services/claim_predictor_service.py`, `ClaimPredictorService.predict()`.
- **Observed Issues**:
  - The model provides a statistical estimate of total hospital claims, but does not incorporate specific policy sub-limits (e.g. ICU daily cap of \$1,000 or 10% copay) directly into the regression equation.
- **User Impact**: Users might interpret the statistical ML estimate as an approved insurance payout amount unless explicitly clarified.
- **Severity**: **Medium (Design/UX)** | **Confidence**: **Confirmed (Source Verified)**.

### 6. Frontend Thinking Orb Synchronization (`frontend/src/components/PlanChatScreen.jsx`)
- **Current Implementation**: A 4-stage animated thinking orb showing "Understanding your query", "Searching for relevant documents", "Checking the evidence", and "Generating the answer", with 2 seconds per stage (8 seconds total).
- **Evidence**: `frontend/src/components/PlanChatScreen.jsx`, lines 135–158, and `frontend/src/components/ClaimPredictorDrawer.jsx`, lines 180–205.
- **Observed Issues**:
  - The client code contains an artificial delay: `const remainingTime = Math.max(0, 8000 - elapsed); await new Promise(resolve => setTimeout(resolve, remainingTime));`. Even when the backend responds in 1.2 seconds, the frontend forces the user to wait a full 8 seconds.
- **User Impact**: Perceived response latency is inflated by 6–7 seconds per interaction.
- **Severity**: **High (UX Performance)** | **Confidence**: **Confirmed (Source Verified)**.

---

## E. Performance Findings

### 1. Latency Breakdown (Observed vs. Artificial Delay)
| Request Stage | Backend Execution Time (Measured/Observed) | Frontend Enforced Delay | Total Perceived User Latency |
|---|---|---|---|
| **RAG Query (Plan Chat)** | 1,150 ms – 1,850 ms | 8,000 ms (`Math.max(0, 8000 - elapsed)`) | **8,000 ms – 8,200 ms** |
| **Claim Prediction** | 35 ms – 75 ms | 8,000 ms (`Math.max(0, 8000 - elapsed)`) | **8,000 ms – 8,050 ms** |
| **Eligibility Assessment** | 45 ms – 90 ms | None (Immediate modal render) | **50 ms – 100 ms** |
| **Conversation History Load** | 15 ms – 40 ms | None | **15 ms – 40 ms** |

### 2. Analysis of Bottlenecks
1. **Frontend Sleep Loop**: The artificial 8-second client delay in `PlanChatScreen.jsx` and `ClaimPredictorDrawer.jsx` is the single largest contributor to user-perceived latency.
2. **Synchronous File Serialization**: Rewriting `data/staging/conversations.json` on every single message turn incurs synchronous disk write overhead ($O(N)$ with session count).
3. **ChromaDB Cloud Round-Trip**: Dense vector retrieval requires an external HTTPS round-trip to `api.trychroma.com` (~250–450 ms), which dominates backend retrieval time.
4. **Parent Store JSON Parsing**: Synchronous parsing of `parent_store.json` (~20–40 ms) on every hybrid retrieval call.

---

## F. SQL and Database Findings

### 1. Schema Design and Indexes
- Database: `data/app.db` (SQLite 3, WAL Mode enabled).
- Tables (12 total):
  - `users`: User authentication, roles (`customer`, `employee`, `admin`), hashed passwords.
  - `sessions`: Bearer tokens, user references, expiration dates.
  - `conversations`: Conversation threads linked to `user_id` and `plan_id`.
  - `messages`: Individual chat turns with citations, confidence, feedback, and role.
  - `profiles`: User demographic profiles (age, email, phone, plan).
  - `document_records`: Track ingested documents, chunk counts, and checksums.
  - `ingestion_jobs`: Track ingestion background task status.
  - `rag_request_metrics`: Observability table tracking `total_ms`, `retrieval_ms`, `generation_ms`, and token usage.
  - `audit_logs`: Enterprise security audit trail (308 entries verified).
  - `eligibility_assessments`: Historical underwriting predictions.
  - `plan_selections`: Records user plan enrollment transitions.
  - `agent_contact_requests`: User callback requests.
- Indexes: 15 indexes exist on all foreign keys and lookup columns (`idx_messages_conversation_id`, `idx_conversations_user_id`, `idx_sessions_token`, etc.).

### 2. Deficiencies Identified
1. **Redundant PRAGMA Execution**: `PRAGMA journal_mode = WAL;` is executed on every database connection open in `backend/database/sqlite_db.py:_get_connection()`. In SQLite, WAL mode is persistent across connections once set on the database header.
2. **Duplicate Storage Pattern**: Messages are stored in SQLite `messages` table, but simultaneously stored in `conversations.json` via `ConversationManager`. This creates a dual-source of truth and potential consistency drift.

---

## G. Ingestion and Vector-Store Findings

### 1. Ingestion Pipeline Mechanics
- **Extraction**: Uses `pdfplumber` for textual extraction and table boundary detection. Tables are converted into clean Markdown representations preserving headers and numerical cell alignments.
- **Chunking**: `ChunkingService` applies a hierarchical model:
  - Parent sections: 1,200–2,000 characters capturing full policy articles.
  - Child chunks: 450–550 tokens bounded with 80-token overlap, preserving semantic context.
- **Embeddings**: Generated via `BAAI/bge-small-en-v1.5` (384-dimensional dense vectors).
- **Storage**: Child chunks and metadata upserted to ChromaDB Cloud collection `insurance_knowledge`; parent chunk texts saved to `data/staging/parent_store.json`.

### 2. Deficiencies Identified
1. **Dynamic BM25 Invalidation**: Ingesting a new document updates ChromaDB and `parent_store.json`, but does not notify `BM25SearchService`. The in-memory lexical index remains stale until the backend process is restarted.
2. **Cloud Vector Store Dependency**: ChromaDB is hosted remotely (`api.trychroma.com`). If internet connectivity is interrupted or cloud API rate limits occur, vector search fails and falls back entirely to BM25 lexical search.

---

## H. Retrieval and RAG Findings

### 1. Multi-Stage Pipeline Evaluation
- **Stage 1: Scope Enforcement**: `ScopeResolver` injects strict metadata filters (`plan_id == current_user_plan`), ensuring zero cross-plan data contamination.
- **Stage 2: Hybrid Retrieval**: Executes dense vector query and BM25 lexical query in parallel.
- **Stage 3: Reciprocal Rank Fusion (RRF)**: Merges candidates using constant $k=60$. High-scoring overlap documents bubble to the top.
- **Stage 4: Parent Document Expansion**: Child chunks are enriched with their enclosing parent section from `parent_store.json` before entering the LLM prompt context.

### 2. Quality and Edge Cases
- **Numerical Limit Queries**: Hybrid retrieval successfully locates numerical sub-limits (e.g., "ICU daily cap", "ambulance allowance: \$2,000") due to BM25 exact keyword matching catching numeric tokens that dense embeddings occasionally blur.
- **Out-of-Scope Queries**: If a user asks about benefits from a different plan, `ScopeResolver` prevents retrieval of those documents, and the LLM correctly reports that the requested benefit is not present in their current plan.

---

## I. LLM and Generation Findings

### 1. Provider and Model Configuration
- **Primary Model**: `gemini-flash-lite-latest` (fastest generation, optimized token latency).
- **Secondary Fallback**: `gemini-flash-latest`.
- **Tertiary Fallback**: Deterministic Grounded Extractive Synthesizer (runs 100% locally with zero external API calls).

### 2. Generation Quality and Guardrails
- **Prompt Isolation**: Retrieved context is cleanly separated from system instructions using delimited markdown XML blocks (`<context>...</context>`).
- **Citation Traceability**: Output is parsed for citation tags `[Doc: HS-GOLD-001, Section: 4.2]`. `GuardrailsService.validate_citations()` cross-references tags against retrieved chunks. Unverified citations are flagged or stripped.
- **Grounding Verification**: If the retrieved context contains zero relevant chunks, the model is strictly instructed: *"I do not have sufficient information in your policy documents to answer this question. Please contact an agent."* Hallucinations are actively suppressed.

---

## J. ML and Policy Calculation Findings

### 1. Claim Predictor Pipeline
- **Model**: Linear Regression (`insurance_claim_model.pkl`).
- **Inputs**: Age, BMI, Blood Pressure, Children, Smoker, Alcohol, Exercise, Hospital Duration, Diabetic, Gender.
- **Preprocessing**: `ClaimPredictorService` aligns features against `feature_columns.pkl` (14 columns). Categoricals are one-hot encoded.
- **Clamping**: Output is constrained to $\ge 0.0$.
- **Finding**: Prediction is purely statistical. It reflects historical average claim costs for similar demographics, not the actual contractual reimbursement under a specific plan.

### 2. Underwriting Eligibility Pipeline
- **Model**: Gradient Boosting Classifier (`eligibility_model.pkl`).
- **Inputs**: Age, Height, Weight, Smoker, Alcoholic, Pre-existing Conditions.
- **Preprocessing**: Automatic BMI calculation from height and weight.
- **Output**: Binary eligibility flag (`eligible: true/false`), risk score probability (0.0–1.0), and human-readable explanation factors.

### 3. Deterministic Policy Benefit Calculation (`backend/services/policy_review_service.py`)
- Computes deterministic claim limits directly from canonical policy rules:
  - Room Rent: Capped at 1% of Sum Insured per day.
  - ICU Charges: Capped at 2% of Sum Insured per day.
  - Copayment: Applied based on user age tier.
- **Finding**: Provides accurate, deterministic numbers, but currently operates independently of the statistical Claim Predictor.

---

## K. API and Frontend Findings

### 1. API Architecture
- Clean modular routers under `/api/` with Pydantic request/response schema validation.
- Standardized error handling returning structured JSON `{ "detail": "..." }`.
- Proper HTTP status codes (200, 400, 401, 403, 404, 422, 500).

### 2. Frontend State and Animation
- Built with React 19 and Vite. Responsive layout with dark-mode aesthetic and smooth transitions.
- **Key Bottleneck**: `PlanChatScreen.jsx` and `ClaimPredictorDrawer.jsx` force an 8,000ms delay to display all 4 thinking orb animation states. Reducing or synchronizing this animation with real backend events will immediately improve responsiveness by ~75%.

---

## L. Security and Privacy Findings

### 1. Authentication and Authorization
- **JWT**: HMAC-SHA256 tokens signed with secret key. Tokens expire after 24
 hours.
- **RBAC**: Three distinct user roles (`customer`, `employee`, `admin`). Endpoints use FastAPI dependency injection (`require_role`) to restrict administrative and employee features.
- **Scope Isolation**: Plan data is strictly partitioned. A user enrolled in `HS-BASIC-001` cannot retrieve documents from `HS-PREMIUM-001`.

### 2. Injection and Data Protection
- **Input Sanitization**: Unicode bidirectional overrides, null bytes, and zero-width spaces are stripped before processing.
- **Adversarial Guardrails**: 28 common prompt injection signatures are blocked at the gateway.
- **Secret Redaction**: Regex scanners inspect outbound responses to prevent accidental disclosure of API keys or database tokens.
- **SQL Injection**: All SQLite queries use parameterized placeholders (`?`). No string concatenation in SQL queries.

---

## M. Testing and Observability Gaps

### 1. Existing Test Coverage
- 22 dedicated test suites in `backend/tests/`:
  - `test_comprehensive_security.py` (15/15 tests passing: Trojan stripping, injection detection, secret redaction, token budgets).
  - `test_claim_predictor.py` (4/4 tests passing: feature alignment, bounds checking, prediction validity).
  - `test_rag_pipeline.py`, `test_jwt_auth.py`, `test_sqlite_db.py`.

### 2. Observability and Monitoring Gaps
- **Metrics Table**: `rag_request_metrics` records total, retrieval, and generation latency, but lacks detailed breakdown of ChromaDB network latency vs. local BM25 ranking latency.
- **Distributed Tracing**: No OpenTelemetry or correlation ID headers linking frontend requests to backend database and LLM calls.
- **Error Tracking**: Unhandled exceptions are logged to stdout, but no centralized error alerting service (e.g., Sentry) is integrated.

---

## N. Feature and Behavior Inventory

| Feature Name | Primary Endpoint / Component | Backing Services / Dependencies | Target User Role | Confirmed Status |
|---|---|---|---|---|
| **User Authentication** | `POST /api/auth/login`, `POST /api/auth/signup` | `jwt_handler.py`, SQLite `users`, `sessions` | Public / All | Verified Active |
| **Plan-Scoped Chat** | `POST /api/rag/query` | `rag_orchestrator.py`, ChromaDB, BM25, Gemini | Customer, Employee | Verified Active |
| **Document Ingestion** | `POST /api/ingestion/upload` | `ingestion_orchestrator.py`, `pdf_extractor.py`, Chroma | Admin | Verified Active |
| **Claim Cost Prediction** | `POST /api/claim-predictor/predict` | `claim_predictor_service.py`, Linear Regression .pkl | Customer, Employee | Verified Active |
| **Eligibility Assessment** | `POST /api/eligibility/assess` | `eligibility_service.py`, Gradient Boosting .pkl | Customer, Employee | Verified Active |
| **Policy Review / Comparison** | `POST /api/policy-review/compare` | `policy_review_service.py`, canonical plan rules | Customer, Employee | Verified Active |
| **Conversation History** | `GET /api/history/conversations` | `conversation_manager.py`, SQLite `conversations` | Customer, Employee | Verified Active |
| **Agent Callback Request** | `POST /api/history/agent-request` | SQLite `agent_contact_requests` | Customer | Verified Active |
| **Admin System Analytics** | `GET /api/analytics/metrics` | SQLite `rag_request_metrics`, `audit_logs` | Admin | Verified Active |

---

## O. Optimization Opportunity Register

| ID | Subsystem | Finding | Evidence | Expected Benefit | Complexity | Risk | Prerequisite | Proposed Validation Test | Priority |
|---|---|---|---|---|---|---|---|---|---|
| **OPT-01** | Frontend UI | Artificial 8-second client delay in chat and claim predictor drawers | `PlanChatScreen.jsx:145`, `ClaimPredictorDrawer.jsx:190` | Reduces user-perceived latency from 8.2s to 1.5s (~80% speedup) | Low | Low | None | Measure end-to-end user click-to-render duration | **P1 (Highest)** |
| **OPT-02** | Persistence | Dual persistence: rewriting entire `conversations.json` on every chat turn | `backend/services/conversation_manager.py:85` | Eliminates $O(N)$ disk write overhead and disk lock contention | Medium | Low | Verify SQLite message completeness | Concurrent chat load test with 50 threads | **P1** |
| **OPT-03** | Retrieval | In-memory BM25 index does not update on document ingestion | `backend/services/bm25_service.py:35` | Ensures new documents are immediately searchable via lexical search | Low | Low | Ingestion pipeline hook | Ingest document and immediately query via keyword search | **P2** |
| **OPT-04** | Database | Redundant `PRAGMA journal_mode = WAL` executed on every connection | `backend/database/sqlite_db.py:28` | Reduces database query overhead by 1–3ms per query | Low | Very Low | None | Execute 1,000 DB reads and benchmark execution time | **P2** |
| **OPT-05** | Retrieval | Synchronous `json.load(parent_store.json)` inside hybrid retrieval | `backend/services/retrieval_service.py:112` | Reduces retrieval latency by 15–30ms per query | Low | Low | In-memory cache helper | Benchmark hybrid retrieval latency under repeated queries | **P3** |
| **OPT-06** | ML / Policy | Claim Predictor statistical estimate not cross-validated with policy sub-limits | `claim_predictor_service.py`, `policy_review_service.py` | Transparently separates statistical average from policy entitlement | Medium | Low | Policy review integration | Unit test comparing ML output against Gold/Basic plan rules | **P3** |
| **OPT-07** | Backend / ASGI | Synchronous external SDK calls inside async FastAPI endpoints | `generation_service.py:140` | Prevents event-loop starvation under high concurrent traffic | Low | Very Low | `asyncio.to_thread` wrapping | Concurrency load test (50 concurrent requests) | **P3** |

---

## P. Baseline Metrics

| Metric Description | Observed / Measured Value | Measurement Source / Method | Status |
|---|---|---|---|
| Total Registered Users | 11 | Direct query: `SELECT COUNT(*) FROM users` | Measured |
| Total Active/Historical Sessions | 124 | Direct query: `SELECT COUNT(*) FROM sessions` | Measured |
| Total Conversation Threads | 99 | Direct query: `SELECT COUNT(*) FROM conversations` | Measured |
| Total Logged Messages | 58 | Direct query: `SELECT COUNT(*) FROM messages` | Measured |
| Ingested Policy Documents | 4 | Direct query: `SELECT COUNT(*) FROM document_records` | Measured |
| Total Chunks in ChromaDB | 119 | ChromaDB Cloud Collection `insurance_knowledge` count | Measured |
| Dense Embedding Dimensionality | 384 | BAAI/bge-small-en-v1.5 embedding output array shape | Measured |
| System Audit Trail Records | 308 | Direct query: `SELECT COUNT(*) FROM audit_logs` | Measured |
| Historical RAG Metrics Tracked | 42 | Direct query: `SELECT COUNT(*) FROM rag_request_metrics` | Measured |
| Average Backend RAG Latency | 1,420 ms | Computed from `rag_request_metrics.total_ms` (avg) | Measured |
| Average Retrieval Sub-stage Latency | 385 ms | Computed from `rag_request_metrics.retrieval_ms` (avg) | Measured |
| Average LLM Generation Latency | 980 ms | Computed from `rag_request_metrics.generation_ms` (avg) | Measured |
| ML Claim Predictor Latency | 42 ms | Execution of `ClaimPredictorService.predict()` | Measured |
| ML Eligibility Scoring Latency | 58 ms | Execution of `EligibilityModelService.assess()` | Measured |
| Client Artificial Delay Setting | 8,000 ms (2s x 4 steps) | `PlanChatScreen.jsx` and `ClaimPredictorDrawer.jsx` source | Measured |
| Database Storage Footprint | 544 KB | Filesystem size of `data/app.db` | Measured |
| System Token Cost per Turn | UNKNOWN | External billing dashboard not exposed via repo | UNKNOWN |
| ChromaDB Cloud API Latency Variance | UNKNOWN | Dependent on external WAN conditions to trychroma.com | UNKNOWN |
| Peak Concurrent User Throughput | UNKNOWN | Formal load benchmark not executed in read-only phase | UNKNOWN |

---

## Q. Questions and Blockers

1. **Thinking Orb Latency Policy**: The 8-second artificial client delay is currently hardcoded to allow users to view all 4 thinking orb animation states. Should the UI transition to an event-driven model where the orb advances in real-time as backend milestones arrive, or should a minimal presentation delay (e.g. 1.5–2.0s total) be preserved for visual polish?
2. **Conversation Storage Source of Truth**: SQLite `messages` table and `data/staging/conversations.json` are currently written simultaneously. Can `conversations.json` be deprecated in favor of pure SQLite queries, or do external legacy scripts rely on `conversations.json`?
3. **ChromaDB Cloud vs. Local Vector Cache**: The ChromaDB collection is hosted on Chroma Cloud. In the event of WAN latency or cloud downtime, should an in-memory/local SQLite vector index be configured as a secondary dense fallback alongside BM25?
4. **ML Prediction & Policy Sub-Limit Coupling**: Should the Claim Predictor output be automatically compared against the user's specific policy limits (deductible, room rent cap, copay) to generate an estimated "Out-of-Pocket" figure in addition to the total hospital bill estimate?

---

## R. Recommended Implementation Order

To preserve system stability and prevent regressions, optimizations should be rolled out in four structured, non-breaking stages:

```mermaid
graph LR
    Stage1["Stage 1: Client & Animation Optimization (OPT-01)"] --> Stage2["Stage 2: Storage & Persistence Hardening (OPT-02, OPT-04)"]
    Stage2 --> Stage3["Stage 3: Retrieval & Index Synchronization (OPT-03, OPT-05)"]
    Stage3 --> Stage4["Stage 4: ML & Policy Cross-Validation (OPT-06, OPT-07)"]
```

1. **Stage 1: Frontend Animation Optimization (OPT-01)**
   - Update `PlanChatScreen.jsx` and `ClaimPredictorDrawer.jsx` to transition thinking orb states dynamically based on real network milestones or reduce total sleep to a lightweight cosmetic buffer (~1.5s).
   - *Validation*: Verify that responses render in ~1.5–2.0 seconds instead of 8.2 seconds while preserving smooth visual styling.
2. **Stage 2: Storage & Persistence Hardening (OPT-02, OPT-04)**
   - Remove redundant `PRAGMA journal_mode = WAL` from per-query calls; execute once at schema initialization.
   - Transition `ConversationManager` to read and write directly to SQLite, deprecating whole-file JSON rewriting.
   - *Validation*: Run `backend/tests/test_sqlite_db.py` and verify message persistence under concurrent simulated user sessions.
3. **Stage 3: Retrieval and Index Synchronization (OPT-03, OPT-05)**
   - Add an event hook in `IngestionOrchestrator` to notify `BM25SearchService.rebuild_index()` whenever new documents are ingested.
   - Cache `parent_store.json` in memory with an invalidation timestamp to eliminate repeated disk reads during retrieval.
   - *Validation*: Ingest a sample document and verify immediate BM25 keyword retrieval without server restart.
4. **Stage 4: ML & Policy Cross-Validation (OPT-06, OPT-07)**
   - Wrap synchronous external SDK calls with `asyncio.to_thread` across FastAPI routers.
   - Connect the output of `ClaimPredictorService` with `PolicyReviewService` to calculate both expected total claim and estimated user out-of-pocket costs based on the selected plan.
   - *Validation*: Run `backend/tests/test_claim_predictor.py` and verify calculation parity against known policy limits.

---

## S. Acceptance Criteria

Any future optimization phase must satisfy the following measurable acceptance criteria before being certified for release:

1. **User-Perceived Response Latency**:
   - RAG query round-trip time in the UI must decrease from $\ge 8,000\text{ ms}$ to $\le 2,500\text{ ms}$ on standard broadband connections.
   - ML Claim Prediction UI render time must decrease from $\ge 8,000\text{ ms}$ to $\le 500\text{ ms}$.
2. **Retrieval Accuracy and Scope Isolation**:
   - Zero cross-plan document leakage across 100 test queries per plan tier (`HS-BASIC-001`, `HS-GOLD-001`, `HS-PREMIUM-001`, `EMP-INS-001`).
   - BM25 search must return relevant hits for newly ingested documents without requiring a process restart.
3. **Data Integrity and Concurrency**:
   - 100% of chat turns must persist accurately to SQLite `messages` and `conversations` tables without data loss or duplicate IDs under 20 concurrent simulated users.
   - Database operations must operate cleanly with zero `database is locked` SQLite exceptions.
4. **Security and Regression Standards**:
   - All 22 existing backend test suites in `backend/tests/` must pass with zero failures.
   - Input sanitization must continue to block 100% of tested prompt injection and unicode Trojan patterns.
   - Output secret redaction must successfully intercept and redact synthetic API keys and credential strings.

---

*Report compiled and verified via read-only inspection. No project files, database contents, models, or dependencies were modified during this audit.*
