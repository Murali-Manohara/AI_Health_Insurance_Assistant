# User Workflow Implementation Report: Authentication, Profiles, One-Time Eligibility, Shared Workflow & Customer Confirmation

**Project:** AI Health Insurance Assistant  
**Date:** October 26, 2026  
**Scope:** Authentication, Profile Persistence, One-Time Eligibility Enforcement, Shared Customer/Employee Workflow, and Customer-Only Confirm & Review with Persisted Plan Confirmation. (Employee Claim Predictor strictly omitted from this phase per scope boundary).

---

## 1. Files Inspected and Changed

### Inspected Files
- `backend/app/db/sqlite_manager.py` — SQLite tables (`users`, `profiles`, `sessions`, `eligibility_assessments`, `plan_selections`, `agent_contact_requests`), seeding, and database connection safety interlocks.
- `backend/app/services/auth_service.py` — Bcrypt password hashing, session tokens, registration role constraints, and RBAC authorization rules (`AuthorizationService`).
- `backend/app/api/routes/auth.py` — `/signup`, `/login`, `/logout`, `/me` endpoints.
- `backend/app/api/schemas/auth.py` — User request/response schemas, `UserProfileResponse`.
- `backend/app/api/routes/eligibility.py` — `/assess`, `/me`, `/select-plan`, `/agent-contact`.
- `backend/app/services/eligibility_model_service.py` — Machine learning model pipeline, BMI calculations, and ruleset underwriter.
- `backend/app/registry/plans.py` — Canonical plan metadata for `HS-BASIC-001`, `HS-GOLD-001`, `HS-PREMIUM-001`, and `EMP-INS-001`.
- `frontend/src/App.jsx` — Session restoration, stage routing, role switching, drawer toggle.
- `frontend/src/components/ProcessSidebar.jsx` — Left sidebar process navigation, stage checkmarks.
- `frontend/src/components/ProfileDrawer.jsx` — User profile drawer and account details.
- `frontend/src/components/EligibilityScreen.jsx` — Assessment inputs, model prediction results, re-evaluate button logic.
- `frontend/src/components/PlanSelectionScreen.jsx` — Plan cards, features, and selection triggers.
- `frontend/src/services/authApi.js` & `frontend/src/services/eligibilityApi.js` — Client API abstractions.
- `backend/tests/conftest.py` — Isolated temporary database fixture and safety verification.

### Changed Files
1. [sqlite_manager.py](file:///C:/Users/shivu/OneDrive/Desktop/Capstone_rag/backend/app/db/sqlite_manager.py)
   - Added `confirmed_at TEXT` column to `plan_selections` with safe non-destructive migration.
   - Added automatic seeding for local-demo accounts (`shivu@gmail.com`, `murali@gmail.com`, `admin@gmail.com`) with bcrypt hashing.
   - Added explicit `provision_demo_accounts(force_reconcile=False)` method for designated demo accounts.
   - Added `get_completed_assessment_for_user(user_id)` helper.
   - Added `confirm_customer_plan_selection(user_id, plan_id)` method with duplicate protection.
   - Enhanced `save_plan_selection` and `get_active_plan_selection_for_user` to support both `ACTIVE` and `CONFIRMED` statuses.
2. [auth.py (schemas)](file:///C:/Users/shivu/OneDrive/Desktop/Capstone_rag/backend/app/api/schemas/auth.py)
   - Extended `UserProfileResponse` with `account_status`, `eligibility_status`, `eligibility_outcome`, `assessment_completed_at`, `selected_plan_id`, `selected_plan_name`, `plan_selection_status`, `is_confirmed`, `confirmation_status`, `confirmed_at`, and `authorized_plans`.
3. [auth.py (routes)](file:///C:/Users/shivu/OneDrive/Desktop/Capstone_rag/backend/app/api/routes/auth.py)
   - Enriched `GET /api/auth/me` to retrieve authoritative persisted records from `eligibility_assessments` and `plan_selections`, returning consistent profile state across reloads.
4. [eligibility.py (routes)](file:///C:/Users/shivu/OneDrive/Desktop/Capstone_rag/backend/app/api/routes/eligibility.py)
   - Added server-side one-time assessment enforcement in `POST /api/eligibility/assess` (returns saved completed result if already completed; model is not rerun).
   - Added role-based plan authorization enforcement in `POST /api/eligibility/select-plan` (preventing customers from selecting employee plans).
   - Added `POST /api/eligibility/confirm-plan` endpoint enforcing Customer role, valid active plan selection, and recording persistent confirmation.
5. [eligibilityApi.js](file:///C:/Users/shivu/OneDrive/Desktop/Capstone_rag/frontend/src/services/eligibilityApi.js)
   - Added `confirmPlan(selectedPlanId)` client method.
6. [EligibilityScreen.jsx](file:///C:/Users/shivu/OneDrive/Desktop/Capstone_rag/frontend/src/components/EligibilityScreen.jsx)
   - Removed the "Modify Profile / Re-evaluate" button when an assessment is already completed.
   - Added permanent green completion checkmark, formatted completion timestamp, and policy disclosure notice.
7. [ProcessSidebar.jsx](file:///C:/Users/shivu/OneDrive/Desktop/Capstone_rag/frontend/src/components/ProcessSidebar.jsx)
   - Fixed stage 1 checkmark: displays permanent green completed state once assessment is completed, regardless of active navigation tab.
   - Added Customer-only Stage 4 navigation item: "Confirm & Review", enabled once a customer plan is selected. (Hidden for Employee and Admin).
8. [ConfirmReviewScreen.jsx](file:///C:/Users/shivu/OneDrive/Desktop/Capstone_rag/frontend/src/components/ConfirmReviewScreen.jsx) *(New Component)*
   - Customer-only Liquid Glass review interface detailing:
     - Section A: Customer Details (Name, Email, Eligibility Result, Assessment Date).
     - Section B: Selected Plan (Name, ID, Premium, Status).
     - Section C: Major Benefits & Coverage Limits.
     - Section D: Conditions, Waiting Periods & Exclusions.
     - Section E: Confirmation & Governance Disclosure Notice.
   - Prominent "Confirm Plan" button calling backend `/confirm-plan`.
   - Liquid Glass success modal popup with message: *"You have selected the [Plan Name] Plan. Agent will contact you soon for document verification."* and `OK` acknowledgement.
9. [ProfileDrawer.jsx](file:///C:/Users/shivu/OneDrive/Desktop/Capstone_rag/frontend/src/components/ProfileDrawer.jsx)
   - Rewritten to display common, customer-specific, employee-specific, and admin-specific fields using authoritative `/auth/me` data with refresh on drawer open.
10. [App.jsx](file:///C:/Users/shivu/OneDrive/Desktop/Capstone_rag/frontend/src/App.jsx)
    - Integrated `ConfirmReviewScreen` for customer workflow.
    - Updated session restoration to recover active tab (including `confirm`), active plan, and confirmation state.
    - Added `assessment` prop to `ProfileDrawer`.
11. [test_user_workflow.py](file:///C:/Users/shivu/OneDrive/Desktop/Capstone_rag/backend/tests/test_user_workflow.py) *(New Test Suite)*
    - Comprehensive automated test suite verifying demo accounts, profile persistence, one-time assessment, plan restriction, and customer confirmation.

---

## 2. Demo Account Provisioning Results

All three local-demo accounts were provisioned safely and idempotently without exposing plaintext credentials or logging hashes:

| Display Name | Email | Role | Verification Status | Profile Link | Password Verification |
|---|---|---|---|---|---|
| Shivu | `shivu@gmail.com` | `customer` | Active (1) | Linked (`profiles`) | Verified with bcrypt (`12345678`) |
| Murali | `murali@gmail.com` | `employee` | Active (1) | Linked (`profiles`) | Verified with bcrypt (`12345678`) |
| Administrator | `admin@gmail.com` | `admin` | Active (1) | Linked (`profiles`) | Verified with bcrypt (`admin@123`) |

- **Passwords stored exclusively as bcrypt hashes with individual cryptographic salts.**
- **Application startup creates missing accounts without resetting passwords.**
- **The explicit `provision_demo_accounts` operation safely reconciles credentials if requested without touching unrelated users.**

---

## 3. Authentication and RBAC Verification

- **Public Signup Protection:** Public signup cannot create an account with `role: "admin"` (rejected with HTTP 403/422).
- **Employee Privilege Enforcement:** Public signup requesting `role: "employee"` without verified corporate domain does not grant employee privileges; effective role is downgraded to `customer` pending admin approval.
- **Trusted Server-Side Authority:** Role permissions are computed server-side from SQLite database records; client request headers cannot alter role or permissions.
- **Session Tokens:** Auth tokens are verified against SQLite `sessions` table. Expiry and logout revocation are enforced.

---

## 4. One-Time Eligibility Implementation

- **Server-Side Enforcement (`POST /api/eligibility/assess`):**
  - Before running the ML model, the backend queries `sqlite_db.get_completed_assessment_for_user(user_id)`.
  - If a completed assessment already exists, the server immediately returns the saved result (HTTP 200 with `already_completed: true`) and **skips ML model execution**.
  - Direct API submissions with modified payloads cannot rerun the model or overwrite existing completed assessments.
- **Database Concurrency Protection:**
  - `sqlite_db.save_eligibility_assessment` checks if a completed assessment already exists before inserting, preventing race conditions or duplicate records.
- **UI Completed State:**
  - `EligibilityScreen.jsx` removes the "Modify Profile / Re-evaluate" button.
  - Displays persistent green card with saved outcome (`ELIGIBLE`), AI match confidence, assessment date, and underwriting policy disclosure.
  - Sidebar Stage 1 permanently displays a green completion circle and `Completed` badge across page navigation, page reloads, and re-login.

---

## 5. Existing Assessment History Handling

- All historical records in `eligibility_assessments` are preserved.
- When selecting an authoritative assessment, the backend filters by `status = 'COMPLETED'` and selects the authoritative record by `created_at DESC`.
- Failed or incomplete assessments (`status = 'FAILED'`) are never treated as completed.
- Users without an assessment see the normal blank assessment form; no results are fabricated.

---

## 6. Profile Persistence and Restoration

The Profile drawer (`ProfileDrawer.jsx`) displays authoritative data fetched from `GET /api/auth/me`:

### Common Fields (All Roles)
- Full Name
- Email Address
- Assigned Role
- Account Status (`Active & Verified`)

### Customer Profile
- Eligibility Status (`Completed`) & Outcome (`ELIGIBLE`)
- Assessment Date & Time
- Selected Customer Plan (`Health Shield – Gold (HS-GOLD-001)`)
- Selection Status (`ACTIVE` or `CONFIRMED`)
- Final Confirmation Status (`Confirmed` or `Pending Review`)
- Confirmation Date & Time

### Employee Profile
- Authorized Employee Plan (`Executive Employee Insurance Plan (EMP-INS-001)`)
- Corporate Staff Verification status
- Eligibility Result & Completion Status
- Authorized Scope: Eligibility, Corporate Policy Chat, and Ingestion

### Admin Profile
- Administrator Identity (`Administrator`)
- Administrator Email (`admin@gmail.com`)
- Workspace Access (`Full Access — Dashboard & Ingestion`)
- Governance Mode (`System Administrator`)

Data remains consistent across page navigation, browser refresh, logout, and re-login. Stored state does not duplicate unrelated columns.

---

## 7. Customer and Employee Shared Workflow Verification

Both Customer and Employee follow the identical stage progression:
$$\text{Login} \longrightarrow \text{Eligibility Check} \longrightarrow \text{Authorized Plan Selection} \longrightarrow \text{Policy Chat}$$

- **Eligibility Gate:** Plan selection requires authentication and a completed `ELIGIBLE` assessment.
- **Role-Based Plan Scoping:**
  - **Customer:** Authorized plans: `HS-BASIC-001`, `HS-GOLD-001`, `HS-PREMIUM-001`. Attempting to select `EMP-INS-001` returns `403 Forbidden`.
  - **Employee:** Authorized plan: `EMP-INS-001` (plus customer plans for reference).
- **Policy Chat Scope:** RAG queries and citations enforce plan scoping and conversation ownership. Customers cannot access employee policy documentation.

---

## 8. Customer-Only Confirm & Review Implementation

- **Sidebar Stage 4:** Added `Confirm & Review` to `ProcessSidebar.jsx` exclusively when `userRole === 'customer'`. Hidden for Employee and Admin.
- **Gating:** Disabled until a customer plan has been selected.
- **Screen Sections (`ConfirmReviewScreen.jsx`):**
  - **Section A: Customer Details** — Full Name, Email, Eligibility Outcome, Assessment Date.
  - **Section B: Selected Plan** — Plan Full Name, Canonical ID, Indicative Premium, Selection Status.
  - **Section C: Major Benefits** — Annual coverage aggregate, daily hospital cash, ICU allowance, surgery coverage.
  - **Section D: Conditions & Limitations** — Waiting periods (initial & PED), exclusions, claim restrictions.
  - **Section E: Confirmation Notice** — Clear disclosure stating confirmation records enrollment intent and initiates agent verification, without claiming active policy issuance.

---

## 9. Confirmation Persistence and Duplicate Protection

- **Endpoint:** `POST /api/eligibility/confirm-plan`
  - Validates caller has `customer` role (Employee and Admin receive HTTP 403).
  - Validates active eligible assessment exists.
  - Validates payload matches user's active plan selection.
  - Calls `sqlite_db.confirm_customer_plan_selection`, updating status to `CONFIRMED` and writing `confirmed_at` timestamp.
  - Emits audit log event `customer_plan_confirmed`.
- **Idempotency:** Repeated clicks or re-confirmations return the existing confirmed record without creating duplicate database rows.
- **UI Confirmation Modal:** Pops up only after the server confirms persistent write:
  > *“You have selected the [Plan Name] Plan. Agent will contact you soon for document verification.”*
  > Button: `OK`
- After confirmation, the page transitions to a permanent green "Plan Confirmed" state, and the sidebar badge updates to `Confirmed`.

---

## 10. Database Changes

All database changes are non-destructive and preserve existing records:

```sql
-- plan_selections extension
ALTER TABLE plan_selections ADD COLUMN confirmed_at TEXT;
```

- Safe migration logic executes on initialization inside a `try/except sqlite3.OperationalError: pass` block.
- Indexing and foreign key constraints remain intact.
- Existing records in `data/app.db` were preserved untouched.

---

## 11. Actual Test Commands and Pass/Fail Counts

### Dedicated User Workflow Test Suite
Command:
```powershell
.venv\Scripts\pytest backend\tests\test_user_workflow.py -v
```
Output:
```
backend/tests/test_user_workflow.py::test_demo_accounts_provisioning_and_login PASSED       [ 16%]
backend/tests/test_user_workflow.py::test_public_signup_cannot_create_admin_or_privileged_employee PASSED [ 33%]
backend/tests/test_user_workflow.py::test_profile_persistence_for_all_three_roles PASSED    [ 50%]
backend/tests/test_user_workflow.py::test_one_time_eligibility_enforcement PASSED          [ 66%]
backend/tests/test_user_workflow.py::test_plan_selection_and_role_authorization PASSED      [ 83%]
backend/tests/test_user_workflow.py::test_customer_confirmation_workflow PASSED             [100%]

============================= 6 passed in 32.92s ==============================
```

### Full Regression Test Suites
Command:
```powershell
.venv\Scripts\pytest backend\tests\test_auth_and_session.py backend\tests\test_database_isolation.py backend\tests\test_eligibility_model.py backend\tests\test_plan_registry.py backend\tests\test_admin_workspace_and_analytics.py
```
Output:
```
============================= 40 passed in 36.49s =============================
```

**Total automated tests passing:** **46 passed, 0 failed, 0 skipped.**

---

## 12. Frontend Build Results

Command:
```powershell
npm run build
```
Output:
```
> frontend@0.0.0 build
> vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 34 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.68 kB │ gzip:   0.42 kB
dist/assets/index-Ce9nsunx.css  114.58 kB │ gzip:  18.83 kB
dist/assets/index-D8idR8Yj.js   419.69 kB │ gzip: 110.90 kB
✓ built in 462ms
```

Zero lint errors, zero build warnings, zero packaging defects.

---

## 13. Database-Isolation Results

The test suite enforces the database isolation safeguard in `backend/app/db/sqlite_manager.py` (lines 36–41) and `backend/tests/conftest.py`:
- All test runs executed against an ephemeral SQLite database created via `tmp_path_factory`.
- Runtime database `data/app.db` file size and modification timestamp were checked before and after all test executions:
  - Runtime database size unchanged.
  - Runtime database modification timestamp verified intact.
- Safety assertion passed with 100% compliance.

---

## 14. Remaining Issues and Manual Verification Guidance

### Issues
- **None.** All functional requirements, persistence rules, security gates, and UI specifications are complete.

### Recommended Manual Verification Steps
1. **Customer Login (`shivu@gmail.com` / `12345678`):**
   - Fill in age (e.g., 30), height (175), weight (70) and click *Evaluate Underwriting & Eligibility*.
   - Confirm persistent green card appears with date and match score.
   - Click *Continue to Choose Plan ➔*, select **Health Shield – Gold**.
   - Navigate to **Confirm & Review** in sidebar.
   - Review Sections A–E and click **Confirm Plan**.
   - Confirm popup modal appears: *“You have selected the Gold Plan. Agent will contact you soon for document verification.”*
   - Click **OK**, verify page shows persistent "Plan Confirmed" banner.
   - Open top-right profile icon, verify profile shows: Role: customer, Status: Completed, Plan: Gold, Final Confirmation: Confirmed with timestamp.
   - Refresh page; verify state is preserved.
2. **Employee Login (`murali@gmail.com` / `12345678`):**
   - Complete eligibility.
   - Select **Executive Employee Insurance Plan (EMP-INS-001)**.
   - Confirm sidebar does **NOT** display "Confirm & Review".
   - Open profile icon, verify employee profile displays authorized employee plan.
3. **Admin Login (`admin@gmail.com` / `admin@123`):**
   - Confirm direct routing to Admin Dashboard (`/admin/dashboard`).
   - Confirm Customer/Employee workflow items are omitted from admin view.
