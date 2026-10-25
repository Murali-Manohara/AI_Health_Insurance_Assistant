# Critical Security Hardening & Targeted Fixes Report

**Project:** AI Health Insurance Assistant  
**Workspace:** `C:\Users\shivu\OneDrive\Desktop\Capstone_rag`  
**Date:** October 25, 2026  
**Scope:** Remediation of confirmed defects from `docs/PROJECT_PIPELINE_AUDIT.md` (Authentication, Eligibility Gating, Error Handling, Analytics Alignment, and Telemetry).

---

## 1. Executive Summary & Defect Confirmation Matrix

Each defect identified in the audit report was inspected against the live codebase before modification. The table below outlines verification status, root causes, and resolution outcomes:

| Defect / Priority | Audit Finding | Verification Status | Resolution Summary |
|---|---|---|---|
| **Priority 1: Role Header Fallback** | `get_current_user` accepted `X-User-Role: employee` without a token on `/api/plans` and `/api/conversations`. | **Confirmed** in `backend/app/services/auth_service.py` (lines 221–241). | Removed all unauthenticated header fallbacks (`X-User-Role`, `guest_user`, `test_user`). Unauthenticated requests fail closed with `401 Unauthorized`. |
| **Priority 2: Chat Workflow Gating** | `/api/conversations` allowed customer chat creation without checking completed eligibility assessment or active plan selection. | **Confirmed** in `backend/app/api/routes/conversations.py`. | Enforced multi-stage invariant check: Customer must have completed, current, non-expired `ELIGIBLE` assessment, active plan selection matching requested plan, and within qualifying tiers. |
| **Priority 3: Plan Selection Error Swallowing** | `handleSelectPlan` in `frontend/src/App.jsx` caught `eligibilityApi.selectPlan` failure and still advanced to chat. | **Confirmed** in `frontend/src/App.jsx` (lines 146–155). | Removed error swallowing. Chat transition only executes after successful server persistence. Added UI error banner and duplicate submission protection. |
| **Priority 4: Assessment Restoration** | Returning users were routed to plan selection based on `has_assessment` alone, even if ineligible. | **Confirmed** in `frontend/src/App.jsx` (lines 98–111, 56–78). | Conditioned navigation strictly on `outcome === 'ELIGIBLE'`. Ineligible, review, failed, or undetermined assessments remain on eligibility screen. |
| **Priority 5 & 6: Admin KPI Mismatches** | Frontend expected `users_not_assessed`, `users_selected_plan`, `users_proceeded_to_chat` and top-level conversion rates; backend returned differing keys. | **Confirmed** in `sqlite_manager.py` and `AdminDashboardPage.jsx`. | Harmonized backend to return both canonical and alias keys, flattened funnel conversion rates, and updated frontend with fallback lookups and `N/A` handling. |
| **Priority 7: Misleading Latency Fallback** | Hardcoded `450.0 ms` fallback in `sqlite_manager.py:962` manufactured telemetry when no samples existed. | **Confirmed** in `backend/app/db/sqlite_manager.py` (line 962). | Replaced fallback with `None` (`null` in JSON). Frontend renders `N/A` when telemetry is absent. |
| **Priority 8: Hardcoded Admin API URL** | `adminApi.js` hardcoded `http://127.0.0.1:8000/api/admin`. | **Confirmed** in `frontend/src/services/adminApi.js` (line 3). | Replaced with relative `/api/admin` base and centralized `safeFetch` fallback matching `authApi` and `eligibilityApi`. |

---

## 2. Detailed Files Modified & Rationale

### 1. `backend/app/services/auth_service.py`
- **Changes:** Removed lines inspecting `X-User-Role` header and fallback assignment of `guest_user` / `test_user` when Authorization header is missing.
- **Rationale:** Prevents privilege escalation and unauthorized access. Server-side token validation is mandatory for all protected endpoints.

### 2. `backend/app/services/conversation_service.py`
- **Changes:** Removed `guest_user` and `test_user` exemptions in `get_conversation`.
- **Rationale:** Strictly enforces conversation ownership boundaries (`session.user_id != user_id and role != "admin"`).

### 3. `backend/app/services/rag_orchestrator.py`
- **Changes:** Passed authenticated user role `user.role` to `get_conversation` on every multi-turn query turn.
- **Rationale:** Ensures runtime role-plan permissions are continuously validated during active chat sessions.

### 4. `backend/app/api/routes/conversations.py`
- **Changes:**
  1. Enforced `AuthorizationService.is_plan_authorized(user.role, req.selected_plan_id)` upfront.
  2. For `customer` role:
     - Verified `get_current_assessment_for_user`: must exist, `status == 'COMPLETED'`, `outcome == 'ELIGIBLE'`.
     - Verified `expires_at`: must not be expired.
     - Verified `get_active_plan_selection_for_user`: must exist, `status == 'ACTIVE'`.
     - Verified `active_selection.selected_plan_id == req.selected_plan_id`.
     - Verified `active_selection.assessment_id == assessment.assessment_id`.
     - Verified `req.selected_plan_id in assessment.qualifying_plans`.
- **Rationale:** Eliminates bypass where unassessed or ineligible users could initiate policy consultations.

### 5. `frontend/src/App.jsx`
- **Changes:**
  - `handleSelectPlan`: Awaits `eligibilityApi.selectPlan(plan.plan_id)` without swallowing errors. Only advances tab to `'chat'` and persists session state on success.
  - `handleLoginSuccess`: Checks `eligData.assessment.outcome === 'ELIGIBLE'` before setting active tab to `'plans'`. Non-eligible statuses stay on `'eligibility'`.
  - `restoreSession`: Clears saved plan and routes to `'eligibility'` if assessment is not `ELIGIBLE`.
- **Rationale:** Aligns frontend navigation with backend underwriting invariants.

### 6. `frontend/src/components/PlanSelectionScreen.jsx`
- **Changes:**
  - Added `submittingPlanId` state to lock UI against double-clicks.
  - Wrapped `onSelectPlan` call in try/catch to display error banner upon failure.
  - Removed deprecated `X-User-Role` header from plan fetch.
- **Rationale:** Prevents UI desynchronization and duplicate submissions.

### 7. `backend/app/db/sqlite_manager.py`
- **Changes:**
  - Line 962: Removed `or 450.0`. Returns `round(float(met_row["avg_latency"]), 1) if met_row["avg_latency"] is not None else None`.
  - Line 988: Provided both `average_response_latency_ms` and `average_latency_ms`.
  - `get_eligibility_pipeline_kpis`: Added frontend aliases `users_not_assessed`, `users_selected_plan`, `users_proceeded_to_chat` alongside canonical names.
  - Flattened funnel conversion rates: `underwriting_eligibility_rate_pct`, `plan_selection_conversion_rate_pct`, `chat_engagement_conversion_rate_pct` while preserving the nested `funnel_rates` dictionary.
- **Rationale:** Eliminates telemetry fabrication and guarantees complete schema compatibility.

### 8. `frontend/src/pages/AdminDashboardPage.jsx`
- **Changes:**
  - Updated KPI cards and funnel steps to check both canonical and alias names (`users_not_assessed ?? not_assessed_users`, etc.).
  - Added `N/A` handling when conversion rates cannot be calculated (zero denominator or missing data).
  - Formatted latency values as `N/A` when null or 0.
- **Rationale:** Accurate presentation of operational telemetry without silent zeros.

### 9. `frontend/src/services/adminApi.js`
- **Changes:** Replaced `http://127.0.0.1:8000/api/admin` with `/api/admin` and implemented `safeFetch` matching `authApi.js`.
- **Rationale:** Centralizes API endpoint configuration and supports relative proxying.

### 10. `backend/app/services/generation_service.py`
- **Changes:** Restored `contains_unverified_notice` evaluation based on actual chunk metadata (`illustrative_unverified`) and appended notice if unverified corporate data was referenced.
- **Rationale:** Restores accuracy for employee plan compliance without altering RAG architecture.

---

## 3. Invariants Enforced

1. **Authentication Invariant:** No client header (`X-User-Role`, `X-Forwarded-Role`, etc.) can grant access to any protected route. All identities must derive from a verified SQLite session token.
2. **Customer Policy Chat Invariant:**
   $$\text{Customer Chat Allowed} \iff \begin{cases} \text{Assessment Status} = \text{COMPLETED} \\ \text{Assessment Outcome} = \text{ELIGIBLE} \\ \text{Assessment Expiry} > \text{NOW}() \\ \text{Active Plan Selection Exists} \\ \text{Selected Plan} = \text{Requested Plan} \\ \text{Requested Plan} \in \text{Qualifying Plans} \end{cases}$$
3. **Plan Isolation Invariant:** Customers can never access `EMP-INS-001` (Executive Employee Plan), neither in conversation creation, message retrieval, nor diagnostic search.
4. **Telemetry Invariant:** Missing latency samples yield `null` / `None`, displaying `N/A` in the UI; no artificial default numbers are introduced.
5. **Database Isolation Invariant:** All pytest test runs execute against an ephemeral SQLite database created in temporary storage. The live production file `data/app.db` is strictly locked and verified untouched.

---

## 4. API Contract & Schema Details

- **No Destructive Database Migrations:** No existing tables, columns, or rows were altered in `data/app.db`.
- **Backward-Compatible Extensions:**
  - `GET /api/admin/overview`: The `kpis` dictionary now provides dual-key aliases:
    - `not_assessed_users` $\leftrightarrow$ `users_not_assessed`
    - `plan_selected_users` $\leftrightarrow$ `users_selected_plan`
    - `policy_chat_active_users` $\leftrightarrow$ `users_proceeded_to_chat`
    - `average_response_latency_ms` $\leftrightarrow$ `average_latency_ms`
    - Top-level funnel rates $\leftrightarrow$ nested `funnel_rates` object.
  - `POST /api/conversations`: Returns `403 Forbidden` with descriptive messages when eligibility or plan criteria are unmet.

---

## 5. Verification & Test Execution Results

All automated tests were run using the project virtual environment (`.venv\Scripts\pytest`).

### Backend Test Results

```
Command:
.venv\Scripts\pytest backend\tests\test_database_isolation.py backend\tests\test_auth_and_session.py backend\tests\test_eligibility_model.py backend\tests\test_admin_workspace_and_analytics.py backend\tests\test_rag_authorization.py backend\tests\test_rag_retrieval_and_chat.py backend\tests\test_targeted_critical_fixes.py -v

Results:
======================== 65 passed in 62.29s (0:01:02) ========================
```

#### Breakdown by Test Module:
1. `backend/tests/test_database_isolation.py`: **3 / 3 passed**
   - Verified that `data/app.db` is strictly isolated during test runs.
2. `backend/tests/test_auth_and_session.py`: **12 / 12 passed**
   - Bcrypt password hashing, session expiration, token revocation, header spoofing prevention.
3. `backend/tests/test_eligibility_model.py`: **13 / 13 passed**
   - Authoritative Gradient Boosting model prediction, BMI computation, validation rules, plan qualification.
4. `backend/tests/test_admin_workspace_and_analytics.py`: **8 / 8 passed**
   - Admin bootstrap seeding, role protection, audit event logging, overview access.
5. `backend/tests/test_rag_authorization.py`: **5 / 5 passed**
   - Customer employee-plan denial, employee corporate access, fail-closed invalid roles, diagnostic search RBAC.
6. `backend/tests/test_rag_retrieval_and_chat.py`: **8 / 8 passed**
   - Scope resolver, BM25 exact search, hybrid RRF provenance, conversation history filtering.
7. `backend/tests/test_targeted_critical_fixes.py`: **16 / 16 passed**
   - Dedicated regression suite for Priorities 1–7.

### Database Integrity Verification
At session teardown, `conftest.py` compared `data/app.db` file size and modification timestamp against their pre-test baselines:
- **Baseline size:** Identical
- **Baseline mtime:** Identical
- **Result:** Safety assertion passed with 0 violations.

### Frontend Production Build
```
Command: npm run build (in frontend/)
Output:
> frontend@0.0.0 build
> vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 33 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.68 kB │ gzip:   0.42 kB
dist/assets/index-CPxbInbK.css  105.70 kB │ gzip:  17.15 kB
dist/assets/index-C7b9mInZ.js   386.66 kB │ gzip: 104.77 kB
✓ built in 137ms
```

---

## 6. Remaining Risks & Observations

1. **Employee Verification Workflow:**
   - As documented in the audit, public signup allows any user to self-select `role: employee` if their email ends in `@insurance.corp`.
   - **Remaining Risk:** While unauthorized header spoofing is blocked, email domain matching alone does not constitute cryptographically verified corporate employment.
   - **Recommendation:** Integrate corporate SSO (SAML 2.0 / OIDC) or require administrator approval before granting active employee status.
2. **Demo Quick-Fill Controls:**
   - Quick-fill buttons for demo credentials exist in the login UI for local demonstration convenience.
   - **Recommendation:** Ensure environment detection disables demo buttons when deployed to public-facing production tiers.
3. **Automated vs. Manual Verification:**
   - **Automated Verification:** 65 unit and integration tests passed, database isolation checks passed, Vite production build succeeded.
   - **Manual UI Verification:** No browser automation was executed during this test run in compliance with instructions.
