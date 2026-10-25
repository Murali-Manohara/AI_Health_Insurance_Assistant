# Health Insurance Eligibility Model Integration Guide

## 1. Overview & Objective

This document defines the integration of the authentic Python machine learning model package (`eligibility_model_package/`) into the AI Insurance Assistant architecture.

All previously invented deterministic rules, arbitrary point tallying, and synthetic risk scores have been completely eliminated. The underwriting eligibility check in Stage 1 is now driven strictly by the trained machine learning pipeline.

---

## 2. Model Package Architecture & Contract

The authoritative model package is located at:
`eligibility_model_package/`

### A. Algorithm & Pipeline Structure
Deserialized from `eligibility_model.pkl`:
- **Estimator**: `sklearn.pipeline.Pipeline`
- **Step 1 (`'preprocess'`)**: `ColumnTransformer`
  - **Numeric features** (`StandardScaler`): `['age', 'bmi']`
  - **Categorical features** (`OneHotEncoder(handle_unknown='ignore')`): `['smoker', 'alcoholic', 'pre_existing_condition']`
- **Step 2 (`'model'`)**: `HistGradientBoostingClassifier(class_weight='balanced', max_depth=3, max_iter=150, random_state=42)`

### B. Feature Specification & Boundaries
| Feature | Type | Constraints | Allowed Values / Formula |
|---|---|---|---|
| `age` | Integer | `18 <= age <= 100` | Years |
| `height_cm` | Float | `100 <= height_cm <= 250` | Centimeters (used to derive BMI) |
| `weight_kg` | Float | `20 <= weight_kg <= 300` | Kilograms (used to derive BMI) |
| `bmi` | Float | Derived | `bmi = round(weight_kg / (height_cm / 100) ** 2, 2)` |
| `smoker` | String | Case-insensitive | `"Yes"`, `"No"` |
| `alcoholic` | String | Case-insensitive | `"Yes"`, `"No"` |
| `pre_existing_condition` | String | Fixed vocabulary | `"Diabetes"`, `"Heart_Disease"`, `"Hypertension"`, `"Multiple"`, `"None"`, `"Not sure"`, `"Other condition"`, `"Thyroid_Disorder"` |

### C. Output Semantics
- Binary prediction label: `1` = `"Yes" (ELIGIBLE)`, `0` = `"No" (INELIGIBLE)`.
- Probability: `MODEL.predict_proba(row)[0, 1]` returns true probability of eligibility (`probability_eligible`), ranging from `0.0` to `1.0`.

---

## 3. Verified Documented Examples

All documented examples from `eligibility_model_package/` were executed against the runtime environment and verified:

1. **Young Healthy Applicant (Example 1)**:
   - Input: `age=28, height_cm=172, weight_kg=68, smoker='No', alcoholic='No', pre_existing_condition='None'`
   - Output: `{'eligible': 'Yes', 'probability_eligible': 0.9953, 'bmi': 22.99}`
2. **Middle-Aged Applicant with Hypertension (Example 2)**:
   - Input: `age=45, height_cm=165, weight_kg=82, smoker='No', alcoholic='Yes', pre_existing_condition='Hypertension'`
   - Output: `{'eligible': 'No', 'probability_eligible': 0.0885, 'bmi': 30.12}`
3. **Senior Applicant with Heart Disease (Example 3)**:
   - Input: `age=62, height_cm=170, weight_kg=95, smoker='Yes', alcoholic='Yes', pre_existing_condition='Heart_Disease'`
   - Output: `{'eligible': 'No', 'probability_eligible': 0.0, 'bmi': 32.87}`
4. **README Example**:
   - Input: `age=35, height_cm=170, weight_kg=70, smoker='No', alcoholic='No', pre_existing_condition='None'`
   - Output: `{'eligible': 'Yes', 'probability_eligible': 0.9927, 'bmi': 24.22}`

---

## 4. Backend Service Implementation

### Dedicated Service: `EligibilityModelService`
- **File**: `backend/app/services/eligibility_model_service.py`
- **Pattern**: Thread-safe lazy singleton via `EligibilityModelService.get_instance()`.
- **Artifact Path**: Resolved dynamically from workspace root (`PACKAGE_DIR = Path(__file__).resolve().parents[3] / "eligibility_model_package"`), avoiding reliance on process working directory.
- **Fail-Safe Behavior**: If the model artifact cannot be accessed, returns HTTP 500 without defaulting to eligible.

### API Routes: `backend/app/api/routes/eligibility.py`
- `GET /api/eligibility/health`: Model readiness check returning `{ "status": "ready", "model_loaded": true, "metadata": {...} }`.
- `POST /api/eligibility/assess`: Authenticated endpoint receiving applicant biometrics and lifestyle data, executing inference, and persisting the assessment.
- `GET /api/eligibility/me`: Retrieves current active assessment and plan selection for authenticated user.
- `POST /api/eligibility/select-plan`: Gated plan selection verifying user holds an active `ELIGIBLE` assessment covering the chosen plan.
- `POST /api/eligibility/agent-contact`: Submits and persists a request for licensed human agent review.

---

## 5. Persistence Schema

### Table: `eligibility_assessments`
```sql
CREATE TABLE IF NOT EXISTS eligibility_assessments (
    assessment_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL,              -- 'COMPLETED' | 'PENDING' | 'FAILED'
    outcome TEXT NOT NULL,             -- 'ELIGIBLE' | 'INELIGIBLE' | 'NEEDS_REVIEW'
    qualifying_plans_json TEXT,        -- e.g. ["HS-BASIC-001", "HS-GOLD-001", "HS-PREMIUM-001"]
    input_provenance_json TEXT,        -- { age, height_cm, weight_kg, bmi, smoker, alcoholic, pre_existing_condition }
    model_id TEXT,                     -- 'Gradient Boosting'
    model_version TEXT,                -- '1.6.1'
    confidence_score REAL,             -- probability_eligible (e.g. 0.9953)
    reason_codes_json TEXT,            -- ["OUTCOME_ELIGIBLE", "BMI_NORMAL", "SMOKER_NO", ...]
    review_status TEXT,                -- 'NONE' | 'NEEDS_REVIEW'
    error_category TEXT,
    previous_assessment_id TEXT,
    is_current INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    expires_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### Table: `agent_contact_requests`
```sql
CREATE TABLE IF NOT EXISTS agent_contact_requests (
    request_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    assessment_id TEXT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    preferred_contact_method TEXT DEFAULT 'EMAIL',
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (assessment_id) REFERENCES eligibility_assessments(assessment_id) ON DELETE SET NULL
);
```

---

## 6. Role-Based Workflow & Plan Gating

### Customer & Employee Progression
1. **Stage 1: Eligibility Check**
   - User inputs biometrics (Age, Height, Weight) with live BMI calculation.
   - User specifies Smoker ("Yes"/"No"), Alcohol ("Yes"/"No"), and Pre-existing Condition.
   - Evaluated by Gradient Boosting model pipeline.
2. **Stage 2: Choose Plan (Gated)**
   - Unlocked only after server-side verification of an active `ELIGIBLE` assessment.
   - Customers qualify for: `HS-BASIC-001`, `HS-GOLD-001`, `HS-PREMIUM-001`.
   - Corporate Employees qualify for: `EMP-INS-001` + standard tiers.
   - Ineligible applicants cannot select any plan directly.
3. **Stage 3: Policy Chat**
   - Scoped strictly to the authorized selected plan.
4. **Agent Assistance Path**
   - Ineligible applicants receive a clear, evidence-based explanation and a "Contact a Licensed Agent" action.
   - Submits contact request to SQLite database, providing immediate confirmation with a tracking ID.

---

## 7. Test Execution & Verification

### Test Commands
```bash
# Run isolated test suite
.\.venv\Scripts\python.exe -m pytest backend/tests/test_database_isolation.py backend/tests/test_auth_and_session.py backend/tests/test_eligibility_model.py

# Verify frontend build
npm run build --prefix frontend
```

### Observed Results
- `test_database_isolation.py`: 3/3 passed.
- `test_auth_and_session.py`: 12/12 passed.
- `test_eligibility_model.py`: 13/13 passed.
- **Total**: 28 passed in 36.83s.
- `npm run build`: built in 141ms with 0 errors.
- Runtime database `data/app.db` remained strictly untouched with exactly 5 authentic accounts.
