# End-to-End Project Pipeline & Architecture Audit Report
**Project:** AI Health Insurance Assistant  
**Date of Audit:** October 25, 2026  
**Audit Type:** Read-Only Technical Architecture, User Journey, ML Underwriting, Database, and Security Audit  
**Authoritative Location:** `docs/PROJECT_PIPELINE_AUDIT.md`  

---

## Section 1 — Executive Summary

This comprehensive audit was conducted to verify whether the AI Insurance Assistant implementation adheres to its intended business architecture, role-based workflows, machine learning underwriting integration, data persistence guarantees, security boundaries, and administrative telemetry.

### Core Architecture Alignment Assessment

| Architectural Domain | Expected Architecture | Current Implementation Status | Compliance Assessment |
|---|---|---|---|
| **Role Architecture** | Customer, Employee, Admin | Customer, Employee, Admin with server-side RBAC | **COMPLIANT** |
| **Workflow Progression** | Sign In → Eligibility Check (ML) → Choose Plan → Policy Chat | Frontend enforces progression; Backend has partial gating gaps | **PARTIAL COMPLIANCE** |
| **Eligibility ML Engine** | Authentic `HistGradientBoostingClassifier` Pipeline | Integrated via `EligibilityModelService` with authentic feature schema | **COMPLIANT** |
| **User Registration & Profile** | Form fields validated, persisted, displayed, passwords protected | Full signup/login pipeline persisted; Profile editing not implemented | **COMPLIANT (Read-Only)** |
| **Demo Account Infrastructure** | Pre-seeded accounts for Customer, Employee, Admin | Seeded in SQLite with bcrypt credentials in `RUNBOOK.md` | **COMPLIANT** |
| **Plan Selection Gating** | Unlocked only after server-verified `ELIGIBLE` assessment | Enforced on `/eligibility/select-plan`, but not on `/conversations` | **PARTIAL COMPLIANCE** |
| **Policy Chatbot Scoping** | Plan-scoped RAG; Employee plan strictly quarantined from Customer | Multi-layer boundary (`ScopeResolver`, chunk sanitization, refusal notice) | **COMPLIANT** |
| **Admin Analytics & Funnel** | Real-time SQLite KPIs and conversion funnel | Backend queries authentic tables; Frontend has field key mismatches | **DEFECTS IDENTIFIED** |
| **PDF Ingestion Authorization** | Exclusively restricted to Admin on backend | Protected by `Depends(get_admin_user)` and session validation | **COMPLIANT** |
| **Database & Test Isolation** | Production `data/app.db` isolated from automated test suite | Strict safeguard in `sqlite_manager.py` prevents test contamination | **COMPLIANT** |

### High-Level Summary of Findings
1. **Machine Learning Underwriting Integrity**: The authentic machine learning pipeline (`HistGradientBoostingClassifier` with `StandardScaler` and `OneHotEncoder`) located in `eligibility_model_package/` is genuinely driving the underwriting workflow. All previously invented rules (hardcoded age 65 cutoff, arbitrary points deduction, and employee automatic exemptions) have been completely removed.
2. **Backend Chatbot Plan Gating Gap**: While `POST /api/eligibility/select-plan` strictly verifies that an applicant holds an active `ELIGIBLE` assessment, `POST /api/conversations` (which initializes the chatbot session) only verifies that the user's *role* has access to the plan. An unassessed or ineligible user can directly invoke `/api/conversations` via API tools and chat with policy documents.
3. **Frontend Error Swallowing on Plan Selection**: In `frontend/src/App.jsx:handleSelectPlan`, a failed call to `/api/eligibility/select-plan` catches the error and still advances the user to the chatbot interface (`setActiveTab('chat')`).
4. **Admin Dashboard KPI Key Mismatches**: Several KPI cards and funnel steps on `frontend/src/pages/AdminDashboardPage.jsx` reference property names that differ from those returned by `backend/app/db/sqlite_manager.py` (e.g. `users_not_assessed` vs `not_assessed_users`, `users_selected_plan` vs `plan_selected_users`), causing several metrics to render as `0` or `0%` despite accurate database calculations.
5. **Development Header Fallback Vulnerability**: `auth_service.py:get_current_user` allows unauthenticated callers presenting `X-User-Role: employee` to query `/api/plans` and `/api/conversations` as `"test_user"` without credentials.

---

## Section 2 — Actual Application Architecture

The active repository operates as a decoupled client-server architecture with an embedded Python machine learning underwriting service, a dual vector/BM25 retrieval engine, and an ACID-compliant SQLite operational store.

```
+---------------------------------------------------------------------------------------+
|                                     FRONTEND UI                                       |
|  React 18 + Vite | Apple Liquid Glass Design System | Google Fonts (BJCree, PT Serif) |
|  Routes & Components: LoginScreen, SignupScreen, EligibilityScreen, PlanSelection,   |
|                       PlanChatScreen, ProfileDrawer, AdminDashboardPage               |
+---------------------------------------------------------------------------------------+
                                           | HTTP (JSON / Bearer Token)
                                           v
+---------------------------------------------------------------------------------------+
|                                   BACKEND (FastAPI)                                   |
|  app/main.py -> Routers: /auth, /eligibility, /plans, /conversations, /upload, /admin |
+---------------------------------------------------------------------------------------+
         |                                 |                             |
         v                                 v                             v
+-----------------------+     +--------------------------+     +------------------------+
|  AUTHENTIC ML ENGINE  |     |   HYBRID RAG PIPELINE    |     |    OPERATIONAL DB      |
|  eligibility_model_   |     |  rag_orchestrator.py     |     |  SQLite: data/app.db   |
|  package/             |     |  - ScopeResolver         |     |  12 Schema Tables:     |
|  - StandardScaler     |     |  - BM25 + Chroma Dense   |     |  - users, sessions     |
|  - OneHotEncoder      |     |  - RRF Rank Fusion       |     |  - profiles            |
|  - HistGradient-      |     |  - Generation Service    |     |  - eligibility_asmt    |
|    BoostingClassifier |     |    (Gemini 2.5 Flash)    |     |  - plan_selections     |
|  - Singleton Wrapper  |     |  - Citation Injection    |     |  - conversations, msg  |
|  - BMI derivation     |     |  - Plan Isolation Guard  |     |  - audit_logs          |
+-----------------------+     +--------------------------+     +------------------------+
```

### Component Details
- **Frontend Layer**: Built using React 18 and Vite v8.3.5. Styling is implemented using pure Vanilla CSS adhering to the Apple-inspired Liquid Glass design language (`#007AFF`, `#F5F5F7`, `#FFFFFF`, `#1D1D1F`, glass blur, specular highlights).
- **API & Middleware Layer**: FastAPI running on Python 3.12 with Pydantic v2 schemas. Authentication uses Bearer session tokens stored in SQLite.
- **Underwriting Machine Learning Layer**:authoritative pipeline deserialized from `eligibility_model_package/eligibility_model.pkl` using `scikit-learn==1.6.1`. Wrapped as a lazy singleton in `EligibilityModelService`.
- **RAG & Knowledge Retrieval Layer**: Ingestion coordinates 9 distinct stages, chunking PDFs into parent-child chunks and storing dense vectors in ChromaDB Cloud (`insurance_knowledge` collection) alongside an in-memory BM25 index. Query routing uses `ScopeResolver` and Reciprocal Rank Fusion (RRF).
- **Database & Storage Layer**: SQLite database located at `data/app.db` maintaining referential integrity and strict automated test isolation.

---

## Section 3 — Role Matrix & Permissions

The system implements three mutually exclusive roles enforced across both API endpoints and retrieval scopes:

| Capability / Resource | Customer | Corporate Employee | Compliance Admin | Enforcement Mechanism |
|---|---|---|---|---|
| **Public Registration** | Self-serve registration (`/auth/signup`) | Request allowed; requires `@insurance.corp` for immediate approval | Forbidden; registration attempts rejected with HTTP 403 | `auth_service.py:register_user` |
| **Eligibility Assessment** | Mandatory ML Underwriting (`/eligibility/assess`) | Mandatory ML Underwriting (`/eligibility/assess`) | May inspect or assess | `eligibility.py:assess_applicant_eligibility` |
| **Public Health Plans** (`HS-BASIC-001`, `HS-GOLD-001`, `HS-PREMIUM-001`) | Full Access upon ELIGIBLE outcome | Full Access upon ELIGIBLE outcome | Full Access | `auth_service.py:ROLE_PLAN_PERMISSIONS` |
| **Corporate Employee Plan** (`EMP-INS-001`) | **FORBIDDEN** (filtered from API, scope resolver, and citations) | Full Access upon ELIGIBLE outcome | Full Access | `auth_service.py:EMPLOYEE_ONLY_PLANS` |
| **Plan Comparison Queries** | Permitted across customer plans only | Permitted across all 4 plans | Permitted | `scope_resolver.py:resolve_scope` |
| **Policy Chatbot Access** | Plan-scoped; active selected plan required | Plan-scoped; active selected plan required | Full inspection | `conversations.py` & `PlanChatScreen.jsx` |
| **Agent Assistance Submission** | Allowed (`/eligibility/agent-contact`) | Allowed (`/eligibility/agent-contact`) | Can view in Admin Dashboard | `eligibility.py:request_agent_contact` |
| **Admin Dashboard Overview** | **FORBIDDEN** (HTTP 403) | **FORBIDDEN** (HTTP 403) | Full Access | `admin_dashboard.py:get_admin_user` |
| **User Account Approval** | **FORBIDDEN** (HTTP 403) | **FORBIDDEN** (HTTP 403) | Can toggle active/suspended | `admin_dashboard.py:update_user_status` |
| **Document Ingestion & Upload** | **FORBIDDEN** (HTTP 403) | **FORBIDDEN** (HTTP 403) | Exclusive access (`/upload`, `/ingestion`) | `upload.py` & `ingestion.py` |

---

## Section 4 — Workflow Stage-by-Stage Comparison

### Intended Workflow
$$\text{SIGN UP} \longrightarrow \text{SIGN IN} \longrightarrow \text{ELIGIBILITY CHECK (ML)} \longrightarrow \text{CHOOSE PLAN} \longrightarrow \text{POLICY CHATBOT} \longrightarrow \text{FUTURE STAGE}$$

### Detailed Stage Evaluation

```
+------------------+--------------------------------------------------+--------------------------------------------------+--------------------+
| Workflow Stage   | Intended Business Behavior                       | Actual Observed Implementation                   | Conformance Status |
+------------------+--------------------------------------------------+--------------------------------------------------+--------------------+
| 1. Sign Up       | User provides name, email, role, password.       | SignupScreen validates regex, passwords (>=8),   | COMPLIANT          |
|                  | Employee requires corporate verification.        | checks domain, hashes with bcrypt, saves user.   |                    |
+------------------+--------------------------------------------------+--------------------------------------------------+--------------------+
| 2. Sign In       | Authenticate against SQLite, generate session,   | Authenticates bcrypt hash, creates session in    | COMPLIANT          |
|                  | check prior assessment, route to stage.          | SQLite, loads prior assessment via /me.          |                    |
+------------------+--------------------------------------------------+--------------------------------------------------+--------------------+
| 3. Eligibility   | Collect 6 model inputs, compute BMI, run ML      | EligibilityScreen collects age, height, weight,  | COMPLIANT          |
|    Check (ML)    | prediction, persist assessment, return outcome.  | lifestyle, condition. Runs Gradient Booster.     |                    |
+------------------+--------------------------------------------------+--------------------------------------------------+--------------------+
| 4. Choose Plan   | Gated strictly to ELIGIBLE users. Persist        | Backend /select-plan strictly enforces ELIGIBLE; | PARTIAL            |
|                  | selection. Ineligible redirected to Agent.       | Frontend swallows error; /conversations lacks it.|                    |
+------------------+--------------------------------------------------+--------------------------------------------------+--------------------+
| 5. Policy Chat   | Unlocked after valid plan selection. RAG search  | Full hybrid RAG with citations, speech-to-text,  | COMPLIANT          |
|                  | strictly scoped to selected plan & role limits.  | text-to-speech, and employee quarantine.         |                    |
+------------------+--------------------------------------------------+--------------------------------------------------+--------------------+
| 6. Future Stage  | Underwriting binder / policy generation.         | Intentionally planned for future implementation. | N/A (Planned)      |
+------------------+--------------------------------------------------+--------------------------------------------------+--------------------+
```

---

## Section 5 — Signup and User Profile Complete Data Path Audit

We audited the complete lifecycle of registration fields from form inputs to database columns and profile presentation:

```
[SignupScreen Form] 
       | (fullName, email, role, password, confirmPassword)
       v
[Client Validation] 
       | (Email regex, password min 8, password confirmation check)
       v
[API Payload: POST /auth/signup]
       | { "email": str, "password": str, "role": str, "full_name": str }
       v
[Backend Schema: SignupRequest]
       | Validates email regex, password min 8, role in ['customer', 'employee']
       v
[Auth Service: register_user]
       | Checks duplicate email; rejects 'admin'; verifies employee corporate domain;
       | hashes password with bcrypt salt; creates user & session
       v
[Database Persistence]
       | Table `users`: (user_id, email, password_hash, requested_role, effective_role, is_approved, full_name, created_at)
       | Table `profiles`: (user_id, email, role, governance_status, last_login)
       v
[Profile API: GET /auth/me]
       | Returns: { user_id, email, role, full_name, is_approved, governance_status, created_at }
       v
[Frontend Display: ProfileDrawer]
       | Renders Avatar initial, Display Name, Email, Role Tag, Session Status, Active Plan Scope
```

### Field-by-Field Lifecycle Matrix

| Form Field | Collected | Validated | Persisted Table & Column | Returned in Profile API | Displayed in Profile UI | Editable in Profile | Passwords Protected? |
|---|---|---|---|---|---|---|---|
| `Full Name` | Yes (`id="signup-name"`) | Yes (string trim) | `users.full_name` | Yes (`full_name`) | Yes (`displayName`) | No | N/A |
| `Email Address` | Yes (`id="signup-email"`) | Yes (RFC regex) | `users.email`, `profiles.email` | Yes (`email`) | Yes (`currentUser.email`) | No | N/A |
| `Account Role` | Yes (Radio pill) | Yes (`customer`/`employee`) | `users.requested_role`, `users.effective_role`, `profiles.role` | Yes (`role`) | Yes (`user-role-tag`) | No (Admin only) | N/A |
| `Password` | Yes (`id="signup-password"`) | Yes (min 8 chars) | `users.password_hash` (bcrypt hash) | **NEVER RETURNED** | **NEVER DISPLAYED** | No | **YES (Salted bcrypt)** |
| `Confirm Password`| Yes (`signup-confirm-pw`) | Yes (exact match) | Discarded after client check | **NEVER RETURNED** | **NEVER DISPLAYED** | N/A | **YES** |
| `Governance Status`| System-derived | Derived by auth service | `profiles.governance_status` | Yes (`governance_status`) | Yes (`Approval Status`) | No | N/A |
| `Last Login` | System-derived | System timestamp | `profiles.last_login` | Yes (`last_login`) | Implicit | No | N/A |

**Key Profile Finding**: The database architecture maintains two separate tables: `users` and `profiles`. The field `full_name` is stored only in `users`, while `profiles` stores `governance_status` and `last_login`. Profile viewing via `ProfileDrawer.jsx` is strictly read-only. No profile editing endpoints exist.

---

## Section 6 — Demo Accounts Investigation

The application provides pre-configured demo accounts to demonstrate Customer, Employee, and Administrator capabilities without requiring manual registration:

```
+------------------------------------+----------------+---------------------------+---------------------------------------+---------------------+
| Demo Account Email                 | Role           | Database User ID          | Seed Mechanism                        | Password Reference  |
+------------------------------------+----------------+---------------------------+---------------------------------------+---------------------+
| customer@insurance.com             | customer       | user_cust_demo            | sqlite_manager._seed_default_accounts | docs/RUNBOOK.md:124 |
| employee@insurance.corp            | employee       | user_emp_demo             | sqlite_manager._seed_default_accounts | docs/RUNBOOK.md:125 |
| admin@insurance.corp               | admin          | user_admin_demo           | sqlite_manager._seed_default_accounts | docs/RUNBOOK.md:126 |
+------------------------------------+----------------+---------------------------+---------------------------------------+---------------------+
```

### Verification Findings for Demo Accounts
1. **Database Existence**: Verified in `data/app.db`. All 3 accounts exist with matching `user_id`, `is_approved = 1`, and salted bcrypt password hashes.
2. **Profile Records**: All 3 accounts possess corresponding records in `profiles` with active governance statuses (`active_customer`, `verified_employee`, `verified_administrator`).
3. **Frontend Integration**: `LoginScreen.jsx` provides quick-fill demo chips (lines 153–175) that populate email and password fields. No plaintext passwords or credentials are hardcoded in API clients or logs.
4. **Authenticity of Data**: The runtime database `data/app.db` contains exactly **5 authentic user accounts** (the 3 demo accounts plus 2 real organic test accounts: `abc@gmail.com` and `abcd@gmail.com`). All previously fabricated mock users were previously audited and purged.

---

## Section 7 — Eligibility Machine Learning Integration Audit

### Model Pipeline Specification
- **Authoritative Location**: `eligibility_model_package/eligibility_model.pkl`
- **Metadata Configuration**: `eligibility_model_package/model_info.json`
- **Reference Script**: `eligibility_model_package/predict_eligibility.py`
- **Model Architecture**: `sklearn.pipeline.Pipeline`
  - Step 1: `ColumnTransformer`
    - `StandardScaler` applied to `['age', 'bmi']`
    - `OneHotEncoder(handle_unknown='ignore')` applied to `['smoker', 'alcoholic', 'pre_existing_condition']`
  - Step 2: `HistGradientBoostingClassifier(class_weight='balanced', max_depth=3, max_iter=150, random_state=42)`

### Input Feature Contract & Validation
The model strictly expects 6 input features:
1. `age`: Integer $18 \le \text{age} \le 100$.
2. `height_cm`: Float $100.0 \le \text{height\_cm} \le 250.0$.
3. `weight_kg`: Float $20.0 \le \text{weight\_kg} \le 300.0$.
4. `bmi`: Float derived via $\text{round}(\text{weight\_kg} / (\text{height\_cm} / 100)^2, 2)$.
5. `smoker`: Normalized string (`"Yes"` or `"No"`).
6. `alcoholic`: Normalized string (`"Yes"` or `"No"`).
7. `pre_existing_condition`: Strict 8-class vocabulary:
   `"Diabetes"`, `"Heart_Disease"`, `"Hypertension"`, `"Multiple"`, `"None"`, `"Not sure"`, `"Other condition"`, `"Thyroid_Disorder"`.

### Inference & Output Semantics
- Binary prediction: Class `1` $\rightarrow$ `"Yes" (ELIGIBLE)`, Class `0` $\rightarrow$ `"No" (INELIGIBLE)`.
- Confidence: Native probability output via `predict_proba()[0, 1]`, mapped to `probability_eligible`.
- Persistence: Saved in `eligibility_assessments` table. Any prior current assessment for that user is atomically updated to `is_current = 0`.
- Failure Handling: If inference fails or the model artifact is unreachable, the system raises HTTP 500/503. **It never defaults to eligible.**

---

## Section 8 — Plan Selection and Chatbot Access Control Audit

### Frontend vs Backend Gating Analysis

```
[Stage 3: Eligibility Screen]
       | User assesses health data
       | Result: ELIGIBLE or INELIGIBLE
       v
[Stage 4: Plan Selection Screen]
       | Frontend: Checks assessmentResult.outcome === 'ELIGIBLE'
       | Backend: POST /api/eligibility/select-plan checks:
       |          1. User has assessment (403 if missing)
       |          2. outcome == 'ELIGIBLE' (403 if ineligible)
       |          3. plan_id in qualifying_plans (403 if unauthorized)
       v
[Stage 5: Policy Chatbot Screen]
       | Frontend: Opens PlanChatScreen for selectedPlan
       | Backend: POST /api/conversations checks:
       |          1. AuthorizationService.validate_plan_access(role, plan_id)
       |          2. DOES NOT check plan_selections table! (VULNERABILITY)
       |          3. DOES NOT check eligibility_assessments outcome! (VULNERABILITY)
```

### Critical Gating Findings
1. **Server Enforcement on `/select-plan`**: Fully implemented and secure. Calling `POST /api/eligibility/select-plan` without a completed eligible assessment yields HTTP 403 Forbidden.
2. **Missing Server Enforcement on `/conversations`**: `backend/app/api/routes/conversations.py:create_conversation` calls `AuthorizationService.validate_plan_access(role, req.selected_plan_id)`. It validates role permissions, but fails to check whether the user has a valid active record in `plan_selections` or `eligibility_assessments`. Direct API calls to `/conversations` bypass underwriting.
3. **Frontend Plan Selection Catch Handler**: `frontend/src/App.jsx:handleSelectPlan` contains:
   ```javascript
   try {
     await eligibilityApi.selectPlan(plan.plan_id);
   } catch (err) {
     console.warn('Could not persist plan selection to pipeline:', err);
   }
   setSelectedPlan(plan);
   setActiveTab('chat');
   ```
   If the backend rejects `/select-plan`, the error is swallowed and the client interface still transitions into chat.

### Chatbot Retrieval Isolation & RAG Quarantining
- **Retrieval Scope Resolution**: `ScopeResolver.resolve_scope` strips unauthorized plans (such as `EMP-INS-001` for customer queries).
- **Secondary Chunk Sanitization**: `AuthorizationService.sanitize_retrieved_chunks` removes any unauthorized plan chunks before fusion.
- **Refusal Disclaimer**: If a customer queries an employee plan, `generation_service.py` issues a clear refusal banner:
  > *“Access to the Executive Employee Insurance Plan (EMP-INS-001) is restricted to authenticated employees.”*

---

## Section 9 — Administrator Dashboard & Document Ingestion Audit

### PDF Ingestion Pipeline Architecture & Security
- **Route Authorization**: Both `/api/upload` and `/api/ingestion` require `current_user: UserIdentity = Depends(get_admin_user)`.
- **Enforcement**: Non-admin tokens receive HTTP 403 Forbidden. Unauthenticated requests receive HTTP 401.
- **Pipeline Execution**: Runs 9 stages in `IngestionOrchestrator`:
  1. File Validation & SHA-256 Hash
  2. Document Identity Validation
  3. PDF Text & Table Extraction
  4. 17-Section Structure Detection
  5. Parent-Child Chunking
  6. Chunk & Content Validation
  7. Embedding Generation (all-MiniLM-L6-v2)
  8. ChromaDB Vector Store Persistence
  9. Storage Verification & Loss Reporting
- **Tracking**: Ingestion runs are persisted in SQLite tables `document_records` and `ingestion_jobs`, and recorded in `audit_logs`.

### Admin Dashboard Analytics & Metric Source Audit

| Dashboard Metric | UI Display Name | Backend Key Returned | UI Key Expected | Source Table / Query | Status |
|---|---|---|---|---|---|
| Registered Users | `Registered Users` | `total_registered_users` | `total_registered_users` | `SELECT COUNT(*) FROM users` | **ACCURATE** |
| Customer Count | `Customers` | `total_customers` | `total_customers` | `SELECT COUNT(*) FROM users WHERE role='customer'` | **ACCURATE** |
| Staff Count | `Staff` | `total_employees` | `total_employees` | `SELECT COUNT(*) FROM users WHERE role='employee'` | **ACCURATE** |
| Assessed Users | `Assessed for Eligibility` | `total_assessed_users` | `total_assessed_users` | `SELECT COUNT(DISTINCT user_id) FROM eligibility_assessments` | **ACCURATE** |
| Eligible Users | `Eligible Users` | `eligible_users` | `eligible_users` | `COUNT(DISTINCT user_id) WHERE outcome='ELIGIBLE'` | **ACCURATE** |
| Ineligible Users | `Ineligible Users` | `ineligible_users` | `ineligible_users` | `COUNT(DISTINCT user_id) WHERE outcome='INELIGIBLE'` | **ACCURATE** |
| Pending Review | `Pending Review` | `pending_review_users` | `pending_review_users` | `COUNT(DISTINCT user_id) WHERE outcome='NEEDS_REVIEW'` | **ACCURATE** |
| Not Assessed | `Not Assessed` | `not_assessed_users` | `users_not_assessed` | `COUNT(*) FROM users WHERE user_id NOT IN (assessments)` | **DEFECT (Key Mismatch)** |
| Plan Selected | `Plan Selected` | `plan_selected_users` | `users_selected_plan` | `COUNT(DISTINCT user_id) FROM plan_selections` | **DEFECT (Key Mismatch)** |
| Policy Chat Active | `Policy Chat Active` | `policy_chat_active_users` | `users_proceeded_to_chat` | `COUNT(DISTINCT user_id) FROM conversations JOIN messages` | **DEFECT (Key Mismatch)** |
| Underwrite Pass Rate | `Pass Rate` | `funnel_rates.eligibility_rate_pct` | `underwriting_eligibility_rate_pct` | Nested in `funnel_rates` object | **DEFECT (Key Mismatch)** |
| Plan Select Rate | `% of Eligible Users` | `funnel_rates.plan_selection_rate_pct` | `plan_selection_conversion_rate_pct` | Nested in `funnel_rates` object | **DEFECT (Key Mismatch)** |
| Chat Active Rate | `% of Plan Selectors` | `funnel_rates.chat_engagement_rate_pct` | `chat_engagement_conversion_rate_pct` | Nested in `funnel_rates` object | **DEFECT (Key Mismatch)** |

---

## Section 10 — Database & Data-Flow Inventory

### Runtime Database Identity
- **Resolved Database Path**: `c:\Users\shivu\OneDrive\Desktop\Capstone_rag\data\app.db`
- **Database Engine**: SQLite 3 (WAL mode enabled, foreign keys enabled)

### Table Inventory & Persistence Verification

| Table Name | Purpose | Records in Runtime DB | Verified App Writes? | Verified App Reads? | Displayed in UI? | Foreign Key Relationships |
|---|---|---|---|---|---|---|
| `users` | Core user accounts and credentials | **5** | Yes (`auth_service.py`) | Yes (`auth_service.py`, `admin_dashboard.py`) | Yes (`ProfileDrawer`, `AdminDashboardPage`) | Primary user authority |
| `sessions` | Active bearer session tokens | **123** | Yes (`sqlite_db.create_session`) | Yes (`sqlite_db.get_session`) | Yes (Header & Drawer) | `user_id -> users.user_id` |
| `profiles` | Governance metadata & last login | **5** | Yes (`sqlite_db.create_user`) | Yes (`sqlite_db.get_user_by_id`) | Yes (`ProfileDrawer`, `AdminDashboardPage`) | `user_id -> users.user_id` |
| `eligibility_assessments` | ML Underwriting decisions & inputs | **16** | Yes (`eligibility.py`) | Yes (`eligibility.py`, `admin_dashboard.py`) | Yes (`EligibilityScreen`, `AdminDashboardPage`) | `user_id -> users.user_id` |
| `plan_selections` | Bound plan selections per user | **0** | Yes (`eligibility.py`) | Yes (`eligibility.py`, `admin_dashboard.py`) | Yes (`PlanSelectionScreen`, `AdminDashboardPage`) | `user_id -> users.user_id`, `asmt_id` |
| `agent_contact_requests` | Human agent assistance inquiries | **0** | Yes (`eligibility.py`) | Yes (`sqlite_manager.py`) | Yes (`EligibilityScreen` modal) | `user_id -> users.user_id`, `asmt_id` |
| `conversations` | Plan-scoped conversation headers | **24** | Yes (`conversation_service.py`) | Yes (`conversation_service.py`) | Yes (`PlanChatScreen`, `ChatActionsSidebar`) | `user_id -> users.user_id` |
| `messages` | Chat turns, citations, metadata | **14** | Yes (`conversation_service.py`) | Yes (`conversation_service.py`) | Yes (`PlanChatScreen`) | `conv_id -> conversations` |
| `document_records` | Knowledge base document tracking | **4** | Yes (`ingestion_orchestrator.py`) | Yes (`admin_dashboard.py`) | Yes (`AdminDashboardPage` Documents tab) | Bound to `plan_id` |
| `ingestion_jobs` | 9-stage ingestion job telemetry | **4** | Yes (`ingestion_orchestrator.py`) | Yes (`admin_dashboard.py`) | Yes (`AdminDashboardPage` Recent Jobs) | `doc_id -> document_records` |
| `rag_request_metrics` | Retrieval latency & citation metrics | **7** | Yes (`rag_orchestrator.py`) | Yes (`sqlite_manager.py`) | Yes (`AdminDashboardPage` Overview tab) | Bound to `user_id`, `plan_id` |
| `audit_logs` | Security, auth, and pipeline events | **254** | Yes (`sqlite_db.record_audit_event`) | Yes (`admin_dashboard.py`) | Yes (`AdminDashboardPage` Governance Stream) | Bound to `actor_id` |

---

## Section 11 — Security & Role-Isolation Findings

### 1. Development Header Fallback Vulnerability (Medium Severity)
- **File**: `backend/app/services/auth_service.py:221-241`
- **Observation**: If a request does not provide an `Authorization: Bearer` token, `get_current_user` checks for an `X-User-Role` header. While it blocks `admin` role spoofing and `/eligibility` / `/me` endpoints, it permits `X-User-Role: employee` on `/api/plans` and `/api/conversations`.
- **Impact**: An unauthenticated attacker sending `X-User-Role: employee` can query internal corporate plans and execute chatbot conversations without logging in.

### 2. Missing Plan Selection Verification on Chatbot Initialization (High Severity)
- **File**: `backend/app/api/routes/conversations.py:40-62`
- **Observation**: `create_conversation` calls `AuthorizationService.validate_plan_access(role, req.selected_plan_id)`. It verifies whether the user's *role* allows the plan, but does not verify whether the authenticated user has actually completed an assessment or held an active selection in `plan_selections`.
- **Impact**: An authenticated customer can directly POST to `/api/conversations` with `selected_plan_id: "HS-GOLD-001"` without ever taking the eligibility assessment, completely bypassing underwriting.

### 3. Client-Side Plan Selection Error Swallowing (Medium Severity)
- **File**: `frontend/src/App.jsx:146-155`
- **Observation**: When `handleSelectPlan` invokes `eligibilityApi.selectPlan(plan.plan_id)`, any rejection (such as HTTP 403 Forbidden) is caught with `console.warn` and ignored. The frontend immediately updates local state: `setSelectedPlan(plan)` and `setActiveTab('chat')`.
- **Impact**: Ineligible users who manually trigger plan selection in the UI are allowed to view the chat interface.

### 4. Admin API Hardcoded Localhost Origin (Low Severity)
- **File**: `frontend/src/services/adminApi.js:3`
- **Observation**: `const API_BASE = 'http://127.0.0.1:8000/api/admin';` is hardcoded to localhost port 8000 instead of using relative routing `/api/admin` with reverse-proxy fallbacks.
- **Impact**: Admin dashboard API requests fail if hosted under a custom domain, staging IP, or non-default port.

---

## Section 12 — Test Execution & Verification Results

All tests were executed against an isolated SQLite database using the automated test isolation safeguard:

```bash
# Backend Test Execution Command:
.\.venv\Scripts\python.exe -m pytest backend/tests/test_database_isolation.py backend/tests/test_auth_and_session.py backend/tests/test_eligibility_model.py

# Frontend Build Command:
npm run build --prefix frontend
```

### Observed Results Matrix

| Test Suite / Component | Execution Command | Result | Verification Type |
|---|---|---|---|
| **Database Isolation Guard** | `pytest test_database_isolation.py` | **PASS (3/3 passed in 0.12s)** | Execution |
| **Authentication & Session RBAC** | `pytest test_auth_and_session.py` | **PASS (12/12 passed in 1.45s)** | Execution |
| **ML Model Service & Examples** | `pytest test_eligibility_model.py` | **PASS (13/13 passed in 27.59s)** | Execution |
| **Documented Model Example 1 (Young Healthy)** | Direct python execution | **PASS** (`eligible='Yes'`, `prob=0.9953`) | Execution |
| **Documented Model Example 2 (Hypertension)** | Direct python execution | **PASS** (`eligible='No'`, `prob=0.0885`) | Execution |
| **Documented Model Example 3 (Heart Disease)** | Direct python execution | **PASS** (`eligible='No'`, `prob=0.0000`) | Execution |
| **Documented Model Example 4 (README Baseline)** | Direct python execution | **PASS** (`eligible='Yes'`, `prob=0.9927`) | Execution |
| **Frontend Production Build** | `npm run build` | **PASS (33 modules in 138ms, 0 errors)** | Execution |
| **Production DB Immutability** | Read-only row count check | **PASS (5 users intact, 0 test leaks)** | Execution |
| **Chatbot Gating on Server** | Code inspection (`conversations.py`) | **FAIL (Missing plan selection check)** | Static Inspection |
| **Admin KPI Key Mapping** | Code inspection (`AdminDashboardPage.jsx`) | **FAIL (Key mismatch on 6 metrics)** | Static Inspection |

---

## Section 13 — Defect Register

| Finding ID | Severity | Affected Component | Exact Location | Expected Behavior | Actual Observed Behavior | Business / User Impact | Recommended Remediation |
|---|---|---|---|---|---|---|---|
| **DEF-001** | **High** | Backend Chatbot Route | `backend/app/api/routes/conversations.py:40-62` | `create_conversation` must verify that the user has an active `plan_selection` and an `ELIGIBLE` assessment in SQLite. | Endpoint only checks `AuthorizationService.validate_plan_access(role, plan_id)`. | Unassessed or ineligible users can bypass underwriting via API. | Add check `sqlite_db.get_active_plan_selection_for_user(user.user_id)` before creating conversation. |
| **DEF-002** | **High** | Frontend Plan Selection Handler | `frontend/src/App.jsx:146-155` | If `eligibilityApi.selectPlan` fails (HTTP 403), the UI must abort and display an error notice. | Error is swallowed in `catch`, and user is advanced to `setActiveTab('chat')`. | Ineligible users see the chat screen despite rejection. | Block state transition if `selectPlan()` throws an exception. |
| **DEF-003** | **Medium** | Frontend Session Restoration | `frontend/src/App.jsx:98-111` | Ineligible users logging back in should be kept on `eligibility` tab. | `if (eligData && eligData.has_assessment)` advances to `plans` regardless of outcome. | Ineligible users returning to the app are routed to plan selection. | Change condition to check `eligData.assessment.outcome === 'ELIGIBLE'`. |
| **DEF-004** | **Medium** | Frontend Admin Overview | `frontend/src/pages/AdminDashboardPage.jsx:385, 391, 397` | Admin Overview KPI cards should accurately display pipeline metrics. | Keys mismatch: `users_not_assessed`, `users_selected_plan`, and `users_proceeded_to_chat` are undefined. | Cards render `0` instead of real database values. | Update property names to match backend: `not_assessed_users`, `plan_selected_users`, `policy_chat_active_users`. |
| **DEF-005** | **Medium** | Frontend Admin Funnel Rates | `frontend/src/pages/AdminDashboardPage.jsx:362, 392, 398, 496, 504, 512` | Underwriting, selection, and chat conversion percentages should display calculated rates. | Frontend looks for top-level keys like `underwriting_eligibility_rate_pct`, but backend nests them in `funnel_rates`. | Conversion rates render as `0%`. | Reference nested `kpis.funnel_rates.*` or flatten keys in `sqlite_manager.py`. |
| **DEF-006** | **Medium** | Authentication Service | `backend/app/services/auth_service.py:221-241` | Public requests must strictly authenticate via token. | Unauthenticated requests with `X-User-Role: employee` are permitted on `/plans` and `/conversations`. | Role spoofing on non-eligibility endpoints. | Remove `X-User-Role` fallback or restrict it strictly to test environments (`settings.ENV == 'test'`). |
| **DEF-007** | **Low** | Backend Overview KPI Latency | `backend/app/db/sqlite_manager.py:962` | Average latency metric should reflect genuine database telemetry. | Falls back to hardcoded `450.0 ms` if no telemetry exists in time window. | Misleading average latency displayed when activity is sparse. | Return `0.0` or `null` when telemetry records are absent. |
| **DEF-008** | **Low** | Admin API Client | `frontend/src/services/adminApi.js:3` | API requests should use dynamic relative paths. | Hardcodes `http://127.0.0.1:8000/api/admin`. | Fails if hosted on custom domains or remote ports. | Use relative path `/api/admin` with proxy fallback. |

---

## Section 14 — Acceptance Matrix

| Intended Requirement | Status | Summary of Verified Evidence |
|---|---|---|
| **1. Three Roles Implemented (Customer, Employee, Admin)** | **PASS** | Role models in `auth_service.py`, `sqlite_manager.py`, and `AdminSidebar.jsx`. |
| **2. Authentic ML Model Driving Underwriting** | **PASS** | Pipeline loaded from `eligibility_model_package/eligibility_model.pkl`. 4/4 examples verified. |
| **3. Removal of Invented Underwriting Rules** | **PASS** | Obsolete `underwriting_service.py` deleted; hardcoded age/tobacco rules removed. |
| **4. Live Derived BMI Calculation** | **PASS** | Computed in `EligibilityScreen.jsx` and verified in `EligibilityModelService`. |
| **5. Evidence-Based Outcomes (Eligible / Ineligible)** | **PASS** | Continuous probability and deterministic reason codes persisted and displayed. |
| **6. Licensed Agent Contact Workflow** | **PASS** | `agent_contact_requests` table created, API endpoint tested, modal confirmed. |
| **7. Server-Side Plan Selection Gating** | **PARTIAL** | Enforced on `/eligibility/select-plan`, but missing on `/api/conversations`. |
| **8. Retrieval Isolation for Employee Plans** | **PASS** | Multi-layer filtering in `ScopeResolver`, chunk sanitization, and refusal generator. |
| **9. PDF Ingestion Exclusively Restricted to Admin** | **PASS** | Enforced via `Depends(get_admin_user)` on `/upload` and `/ingestion`. |
| **10. Admin Analytics Reflecting Real Database** | **PARTIAL** | Backend queries real SQLite data; frontend has 6 property key mismatches. |
| **11. Test Isolation Safeguard** | **PASS** | Runtime `data/app.db` completely protected during test runs. |
| **12. Liquid Glass Theme Consistency** | **PASS** | Colors, fonts (`BJCree`, `PT Serif`), glass blur, and contrast verified across UI. |

---

## Section 15 — Recommended Fix Order (Prioritized)

For the subsequent, separately authorized implementation phase, corrections should proceed in this sequence:

1. **Gate `/conversations` on the Backend (DEF-001)**:
   Add a verification in `backend/app/api/routes/conversations.py:create_conversation` ensuring the user has an active record in `plan_selections` matching `req.selected_plan_id`.
2. **Prevent Frontend Plan Selection Error Swallowing (DEF-002)**:
   Update `frontend/src/App.jsx:handleSelectPlan` to check `res.ok` and remain on the plans tab if selection is rejected.
3. **Correct Re-login Workflow Routing for Ineligible Users (DEF-003)**:
   In `frontend/src/App.jsx:handleLoginSuccess`, check `eligData.assessment.outcome === 'ELIGIBLE'` before advancing to `'plans'`.
4. **Fix Admin Dashboard KPI Property Keys (DEF-004 & DEF-005)**:
   Align frontend property names in `frontend/src/pages/AdminDashboardPage.jsx` with backend keys from `sqlite_manager.py:get_eligibility_pipeline_kpis`.
5. **Secure Authentication Headers (DEF-006)**:
   Deprecate `X-User-Role` client headers in `backend/app/services/auth_service.py` so that only valid Bearer tokens can authenticate requests.
6. **Normalize Admin API Base URL (DEF-008)**:
   Replace hardcoded `http://127.0.0.1:8000/api/admin` in `frontend/src/services/adminApi.js` with relative URL `/api/admin`.
7. **Clean Latency Telemetry Fallback (DEF-007)**:
   Remove synthetic `450.0 ms` fallback in `sqlite_manager.py:962` to ensure telemetry reporting is 100% grounded in recorded requests.
