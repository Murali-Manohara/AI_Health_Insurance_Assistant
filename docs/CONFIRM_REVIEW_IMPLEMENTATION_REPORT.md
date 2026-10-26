# Implementation Report: Confirm & Review Selected Policy (Single-Screen Desktop Layout)

**Date:** 2026-10-26  
**Status:** Completed & Verified  
**Applicable Plans:** `HS-BASIC-001` (Basic), `HS-GOLD-001` (Gold), `HS-PREMIUM-001` (Premium)  

---

## 1. Executive Summary

This report documents the implementation of the compact, Windows desktop-friendly **Confirm & Review Selected Policy** page for the AI Health Insurance Assistant system. 

The policy details for each plan are loaded strictly and deterministically from their corresponding authorized TXT files (`basic.txt`, `gold.txt`, `premium.txt` located in the `Correct and review` directory), eliminating hardcoded approximations, invented limits, or cross-plan data leakage. Dynamic customer underwriting details are fetched from persisted SQLite backend records, and the layout conforms to the 7-row compact single-screen Windows desktop structure (1440 × 900 and 1366 × 768 at 100% zoom) using the established Liquid Glass visual identity.

---

## 2. Files Inspected & Modified

### Files Inspected:
- `Correct and review/basic.txt`: Specification and verified policy schedule for Health Shield – Basic (`HS-BASIC-001`).
- `Correct and review/gold.txt`: Specification and verified policy schedule for Health Shield – Gold (`HS-GOLD-001`).
- `Correct and review/premium.txt`: Specification and verified policy schedule for Health Shield – Premium (`HS-PREMIUM-001`).
- `backend/app/registry/plans.py`: Plan registry and metadata definitions.
- `backend/app/api/routes/plans.py`: Plan listing endpoints.
- `backend/app/api/routes/eligibility.py`: Assessment retrieval, plan selection, and plan confirmation endpoints.
- `frontend/src/App.jsx`: Global navigation and stage routing.
- `frontend/src/components/ProcessSidebar.jsx`: Stage 4 Confirm & Review gating and locking.
- `frontend/src/components/PlanSelectionScreen.jsx`: Plan selection triggers.

### Files Created & Modified:
1. **`backend/app/services/policy_review_service.py` (New Service):**
   - Implements deterministic mapping between canonical plan IDs and authorized TXT files.
   - Provides canonical normalized structured representations preserving all conditions, amounts, units, and source disclaimers.
2. **`backend/app/api/routes/plans.py` (Modified Endpoint):**
   - Added `GET /api/plans/{plan_id}/review-details` with role authorization check (customer role restricted to customer plans).
3. **`frontend/src/services/eligibilityApi.js` (Modified Service):**
   - Added `getPlanReviewDetails(planId)` with dual-route fallback (`/api/plans/...` and direct backend).
4. **`frontend/src/components/ConfirmReviewScreen.jsx` (Redesigned Component):**
   - Implemented exact 7-row desktop layout matching the ASCII diagram from the source documents.
   - Added dynamic applicant data binding (name, email, role, eligibility status, assessment date).
   - Enforced green checkmark exclusively for `ELIGIBLE` outcome.
   - Rendered 4-card horizontal row for benefits & coverage limits.
   - Rendered two-column layouts for other benefits, waiting periods, exclusions, and claim requirements.
   - Preserved source disclaimers and footer action buttons.
5. **`backend/tests/test_confirm_review_plan_details.py` (New Automated Test Suite):**
   - 7 automated unit and integration tests verifying provenance, values, isolation, RBAC, and error handling.

---

## 3. Plan Documents & Canonical Plan ID Mapping

| Plan Name | Canonical Plan ID | Source TXT Filename | Location | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Health Shield – Basic** | `HS-BASIC-001` | `basic.txt` | `Correct and review/basic.txt` | Fully Verified & Active |
| **Health Shield – Gold** | `HS-GOLD-001` | `gold.txt` | `Correct and review/gold.txt` | Fully Verified & Active |
| **Health Shield – Premium** | `HS-PREMIUM-001` | `premium.txt` | `Correct and review/premium.txt` | Fully Verified & Active |
| **Executive Employee Insurance Plan** | `EMP-INS-001` | *(Pending source file)* | `Correct and review/` | Deferred per user instruction |

---

## 4. Fields Extracted per Plan & Isolation Verification

### 4.1 Health Shield – Basic (`HS-BASIC-001`):
- **Annual Premium:** `₹5,500*` (Payment: Annual only, Taxes: Excluded*).
- **Official Plan Number / UIN:** `Not assigned` / `Not assigned`.
- **Annual Cover:** `Overall annual coverage limit not specified in source document`.
- **Hospital Cash:** `₹2,000 / day` (Min stay >24 hrs, Max 10 days, Max ₹20,000).
- **ICU Benefit:** `₹4,000 / day` (Max 5 days, Max ₹20,000, Relationship: `Additional to hospital cash*`).
- **Major Surgery:** `Basis: ₹2,00,000` (Cat 1: ₹2,00,000 | Cat 2: ₹1,20,000 | Cat 3: ₹80,000 | Cat 4: ₹40,000 | Overall max: `₹6,00,000*`).
- **Other Benefits:**
  - Day-care: `₹10,000/procedure` (Max 1 procedure/year, Max ₹10,000/year).
  - Other surgery: `₹3,000/day` (Max 5 days/year, Max ₹15,000/year).
  - Medical care: `₹5,000/claim` (Max 1 claim/year, Max ₹5,000/year).
  - Extended stay: `₹15,000` (Hospitalization >30 days, Max 1 claim/year).
  - Health check: `Up to ₹1,000/year` (Once per policy year).
  - Ambulance: `Up to ₹250/event` (Max 1 claim/year).
  - Restored cover: `Not included in this plan`.
  - Quick cash: `Not included in this plan`.
  - Optional riders: `Premium waiver: ₹300/year* | Auto Health Cover: ₹500/year* (Not included in base premium)`.
- **Waiting Periods:** Initial illness: `30 days*`, Specified conditions: `24 months*`, PED: `36 months*`, PED lookback: `Previous 36 months*`, Accident: `From policy start*`, Health check: `30 days*`, Premium waiver rider: `90 days*`, Auto Health Cover rider: `From rider start*`.
- **Exclusions:** 6 explicit conditions preserved from `basic.txt`.
- **Claim Requirements:** 7 explicit conditions preserved from `basic.txt`.
- **Disclosure:** *"DEMONSTRATION DATA — NOT AN APPROVED INSURANCE PRODUCT... Confirmation records enrollment intent only; it does not issue a policy, activate coverage, or grant final underwriting approval."*

### 4.2 Health Shield – Gold (`HS-GOLD-001`):
- **Annual Premium:** `₹11,800*` (Payment: Annual, Taxes: Excluded*).
- **Annual Cover:** `Overall annual coverage limit not specified in source document`.
- **Hospital Cash:** `₹5,000 / day` (Min stay >24 hrs, Max 20 days, Max ₹1,00,000).
- **ICU Benefit:** `₹10,000 / day` (Max 10 days, Max ₹1,00,000, Relationship: `ICU and hospital cash combination subject to terms*`).
- **Major Surgery:** `Basis: ₹5,00,000` (Cat 1: ₹5,00,000 | Cat 2: ₹3,00,000 | Cat 3: ₹2,00,000 | Cat 4: ₹1,00,000 | Overall max: `₹25,00,000*`).
- **Other Benefits:**
  - Day-care: `₹25,000/procedure` (Max 2 claims/year, Max ₹50,000/year).
  - Other surgery: `₹10,000/day` (Max 10 days/year, Max ₹1,00,000/year).
  - Medical care: `₹15,000/claim` (Max 2 claims/year, Max ₹30,000/year).
  - Extended stay: `₹50,000` (Hospitalization >30 days, Max 1 claim/year).
  - Health check: `Up to ₹3,000/year` (Once per policy year).
  - Ambulance: `₹500/trip` (Max 2 trips/year).
  - Restored cover: `Up to ₹5,00,000* Once per policy year`.
  - Quick cash: `Up to 25% of eligible surgery benefit; capped at ₹50,000*`.
- **Waiting Periods:** Initial illness: `30 days*`, Specified diseases: `24 months*`, PED: `36 months*`, PED lookback: `Previous 48 months*`, Accident: `From policy start*`, Health check: `30 days*`, Critical illness rider: `90 days*`, Premium waiver rider: `90 days*`.
- **Exclusions:** 7 explicit conditions preserved from `gold.txt`.
- **Claim Requirements:** 7 explicit conditions preserved from `gold.txt`.
- **Disclosure:** *"DEMONSTRATION DATA — NOT AN OFFICIAL VERIFIED INSURANCE PRODUCT..."*

### 4.3 Health Shield – Premium (`HS-PREMIUM-001`):
- **Annual Premium:** `₹22,500*` (Payment: Annual, Taxes: Excluded*).
- **Annual Cover:** `Not specified in source document`.
- **Hospital Cash:** `₹10,000 / day` (Min stay: `Not specified in provided plan document`, Max 30 days, Max ₹3,00,000).
- **ICU Benefit:** `₹20,000 / day` (Max 15 days, Max ₹3,00,000, Relationship: `ICU replaces hospital cash`).
- **Major Surgery:** `Basis: ₹10,00,000` (Cat 1: ₹10L | Cat 2: ₹6L | Cat 3: ₹4L | Cat 4: ₹2L | Overall max: `Not specified in source document`).
- **Other Benefits:**
  - Day-care: `₹50,000/procedure` (Max 3 claims/year, Max ₹1,50,000/year).
  - Other surgery: `₹25,000/day` (Max 15 days/year, Max ₹3,75,000/year).
  - Medical care: `₹25,000/claim` (Max 3 claims/year, Max ₹75,000/year).
  - Extended stay: `₹1,00,000` (Hospitalization >30 days).
  - Health check: `Up to ₹5,000/year`.
  - Ambulance: `₹1,000/claim`.
  - Restored cover: `Not specified in the provided plan document`.
  - Quick cash: `Not specified in the provided plan document`.
- **Waiting Periods:** Initial illness: `30 days*`, Specified ailments: `24 months*`, PED: `36 months*`, PED lookback: `Previous 48 months*`, Accident: `From policy start*`, Rider illness: `30 days*`.
- **Exclusions:** 6 explicit conditions preserved from `premium.txt`.
- **Claim Requirements:** 5 explicit conditions preserved from `premium.txt`.
- **Disclosure:** *"DEMONSTRATION DATA — NOT AN OFFICIAL VERIFIED INSURANCE PRODUCT..."*

---

## 5. Dynamic Applicant Data & Security

1. **Authentication Binding:**
   - Full legal name and registered email are retrieved from the authenticated user token and persisted SQLite user entity.
   - Role is determined by the server-side verified token (`Customer`).
2. **Assessment Binding:**
   - Saved outcome (`ELIGIBLE`, `REVIEW_REQUIRED`, `INELIGIBLE`) and completion date are fetched via `GET /api/eligibility/me`.
   - A green checkmark (`✓`) is rendered **only** when `outcome === 'ELIGIBLE'`. If pending, incomplete, or ineligible, the green checkmark is suppressed.
3. **No Hardcoded Applicant Data:**
   - No mock names, dates, or statuses are hardcoded. If profile details or assessment dates are missing, clear fallback notices ("Not specified in profile", "Not completed") are rendered.

---

## 6. Single-Screen Windows Desktop Layout (1440 × 900 & 1366 × 768)

The layout strictly implements the required 7 rows:
- **Breadcrumb & Header:** Compact uppercase breadcrumb `CHOOSE PLAN > CONFIRM & REVIEW` with subheader.
- **Row 1:** Two side-by-side cards (`01 CUSTOMER DETAILS` and `02 SELECTED PLAN`).
- **Row 2:** Four horizontal cards for `03 BENEFITS & COVERAGE LIMITS` (`ANNUAL COVER`, `HOSPITAL CASH`, `ICU BENEFIT`, `MAJOR SURGERY`).
- **Row 3:** Two side-by-side cards for `04 OTHER BENEFITS` and `05 WAITING PERIODS`.
- **Row 4:** Two columns for `06 EXCLUSIONS & CLAIM REQUIREMENTS`.
- **Row 5:** Compact disclosure panel `07 POLICY DISCLOSURE` with caution heading and asterisk footnote.
- **Footer Actions:** `[ Back to Plan Selection ]` and `[ ✓ Confirm Plan ]`.
- **Visual Design System:** Liquid Glass styling using `#007AFF`, `#AAAAAA`, `#1D1D1F`, `#F5F5F7`, `#FFFFFF`, `#666666`, and `#D6D6D8`. Clean typography, no horizontal overflow, and responsive stacking on smaller mobile viewports.

---

## 7. Confirmation Workflow & Persistence

1. **Backend Validation:**
   - The user must be authenticated with role `customer`.
   - The user must have a completed `ELIGIBLE` assessment.
   - The requested `plan_id` must match the user's active plan selection.
2. **Persistence & Idempotency:**
   - `POST /api/eligibility/confirm-plan` commits confirmation timestamp and updates plan selection status to `CONFIRMED`.
   - Duplicate calls return the existing confirmation timestamp without error (idempotent).
   - Once confirmed, the button locks to `✓ Confirmed (Policy Locked)` and disables re-submission.
3. **User Feedback:**
   - Displays the exact confirmation modal:  
     *"You have selected the [Plan Name] Plan. Agent will contact you soon for document verification."*

---

## 8. Test Execution & Build Results

### Backend Automated Tests:
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\shivu\OneDrive\Desktop\Capstone_rag
collected 7 items

backend\tests\test_confirm_review_plan_details.py .......                [100%]

============================== 7 passed in 4.73s ==============================
```

Full backend regression suite:
```
======================= 102 passed in 108.48s (0:01:48) =======================
```

### Frontend Build:
```
> frontend@0.0.0 build
> vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 34 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.68 kB │ gzip:   0.42 kB
dist/assets/index-Cm7YqgUd.css  114.74 kB │ gzip:  18.95 kB
dist/assets/index-D6Hhngux.js   435.83 kB │ gzip: 113.81 kB

✓ built in 211ms
```
**Build Status:** Clean, 0 errors, 0 warnings.

---

## 9. Remaining Items & Verification

- **Executive Employee Plan (`EMP-INS-001`):** As per the user instruction, the Employee plan document is deferred until its TXT specification file is provided in `Correct and review`.
- All customer policies (`HS-BASIC-001`, `HS-GOLD-001`, `HS-PREMIUM-001`) are verified, functional, isolated, and tested end-to-end.
