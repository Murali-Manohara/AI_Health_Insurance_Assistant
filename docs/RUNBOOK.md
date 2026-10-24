# Operational Runbook — AI Insurance Assistant Platform

**Version:** 2.0.0 (Phase 1 Ingestion + Phase 2 RAG & Chat)  
**Operating System:** Windows 10/11 (Command Prompt `cmd.exe` or PowerShell)  
**Workspace:** `c:\Users\shivu\OneDrive\Desktop\Capstone_rag`  

---

## 1. Prerequisites
- **Python:** 3.12+ (virtual environment located in `.venv`)
- **Node.js:** v20+ and npm (v10+)
- **ChromaDB:** Active Chroma Cloud connection configured in `.env`

---

## 2. Environment Configuration

Navigate to the project root directory:
```cmd
cd /d C:\Users\shivu\OneDrive\Desktop\Capstone_rag
```

Ensure `.env` exists and contains your Chroma Cloud configuration:
```env
CHROMA_MODE=cloud
CHROMA_API_KEY=ck-CvX1WKbLkZXS4NrRf2oe5b7HPkBMNXadoaVLW8oAth8b
CHROMA_TENANT=643b668b-9e6d-4739-ab36-2fcab1d7ad2a
CHROMA_DATABASE=tibil_intern
DATA_DIR=data
```

---

## 3. Step-by-Step Commands to Run the Application

### Step 3.1: Start the FastAPI Backend Server
Open a terminal in the project root and run:

```cmd
cd /d C:\Users\shivu\OneDrive\Desktop\Capstone_rag
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Verification URLs:**
- **Health Check:** `http://127.0.0.1:8000/api/health`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **Plans Registry API:** `http://127.0.0.1:8000/api/plans`

---

### Step 3.2: Start the React Frontend Application
Open a second terminal window and run:

```cmd
cd /d C:\Users\shivu\OneDrive\Desktop\Capstone_rag\frontend
npm run dev
```

**Access the Web Interface:**
- Open your browser to: **`http://localhost:5173`**

---

### Step 3.3: Run the Complete Automated Test Suite (55 Tests)
Run pytest across ingestion, RAG, authorization, authentication, and regression test suites:

```cmd
cd /d C:\Users\shivu\OneDrive\Desktop\Capstone_rag
.venv\Scripts\python.exe -m pytest backend/tests -v
```

Expected result: **55 passed** (Ingestion, RAG, RBAC, Auth, SQLite, and Gold regression tests).

---

### Step 3.4: Run the Universal Response Formatting Evaluation
To execute the 15-archetype live Gemini formatting harness and evaluate directness, scan-friendly structures, disclaimer deduplication, and general knowledge handling:

```cmd
cd /d C:\Users\shivu\OneDrive\Desktop\Capstone_rag
.venv\Scripts\python.exe scripts/evaluate_universal_formatting.py
```

Generated outputs:
- Metric Report: `data/reports/universal_response_format_evaluation.json`
- Markdown Analysis: `data/reports/UNIVERSAL_RESPONSE_FORMAT_REPORT.md`

---

### Step 3.5: Run the RAG Generalization Benchmark (35 Questions)
To execute the multi-category generalization evaluation harness:

```cmd
cd /d C:\Users\shivu\OneDrive\Desktop\Capstone_rag
.venv\Scripts\python.exe scripts/evaluate_rag_generalization.py
```

Generated outputs:
- Metric Report: `data/reports/rag_generalization_evaluation.json`
- Markdown Analysis: `data/reports/RAG_GENERALIZATION_REPORT.md`

---

### Step 3.6: Run the Final Generalization Evaluation (12 Fresh Unseen Questions)
To execute the final validation across fresh unseen queries testing factual accuracy, uncertainty, formatting, and authorization:

```cmd
cd /d C:\Users\shivu\OneDrive\Desktop\Capstone_rag
.venv\Scripts\python.exe scripts/evaluate_final_generalization.py
```

Generated outputs:
- Metric Report: `data/reports/final_generalization_evaluation.json`
- Markdown Analysis: `data/reports/FINAL_GENERALIZATION_REPORT.md`

---

## 4. Live Demonstration Workflow for Mentors & Reviewers

### Demo Step 1: Sign In & Sign Up Flow (Authentication Gate)
1. Open **`http://localhost:5173`** in your browser.
2. Unauthenticated visitors are automatically directed to the **Sign In Screen**. Plan Selection and Chat are guarded and unreachable until authenticated.
3. **Option A (Create New Account):**
   - Click **"Create an Account"**.
   - Enter your email, password (minimum 8 characters), and select a role (**Customer** or **Corporate Employee**).
   - If **Corporate Employee** is chosen with a non-corporate domain, notice the employee protection banner: *"Employee role registration submitted. For security governance, standard customer access is granted pending administrative verification."*
4. **Option B (Quick Demo Logins):**
   - Click the quick demo buttons on the Sign In page:
     - 👤 **Customer Demo:** `customer@insurance.com` / `Customer@123`
     - 🛡️ **Corporate Employee Demo:** `employee@insurance.corp` / `Employee@123`
   - Click **"Sign In"**.

### Demo Step 2: Screen A — Plan Selection Screen
1. On successful login, the application navigates to **Screen A: Choose Plan**.
2. Notice the customer-facing plan cards: **Health Shield – Basic**, **Health Shield – Gold**, and **Health Shield – Premium**.
3. **RBAC Demonstration:**
   - When signed in as **Customer**, only the 3 customer policies are visible.
   - When signed in as **Corporate Employee**, the exclusive **Executive Employee Insurance Plan** card automatically unlocks.
   - The user's verified role and email are displayed in the top right user badge.

### Demo Step 3: Screen B — Plan-Scoped Conversational Chat
1. Click **"Chat with Assistant"** on the **Health Shield – Gold** card.
2. The UI enters Screen B with the policy badge locked to `Health Shield – Gold`.
3. Click a quick inquiry chip: **"Daily Hospital Cash"** or type:
   > *"What is the ICU benefit per day under Gold?"*
4. The assistant responds with the grounded allowance (**Rs. 5,000 per day**) and includes inline bracket citation: `[HS-GOLD-001, Section 3, Chunk 1]`.
5. Click the citation pill below the message to open the **Citation Inspector Drawer**. Inspect the full parent markdown section with the raw benefit table.

### Demo Step 4: Multi-Plan Comparison Query
1. In the chat input, ask:
   > *"Compare Hospital Cash benefits between Basic and Gold."*
2. Observe that the Scope Resolver automatically detects a multi-plan comparison and retrieves context across both `HS-BASIC-001` and `HS-GOLD-001`.
3. Citations from both policies are rendered side-by-side.

### Demo Step 5: Security & Refusal Boundary Enforcement
1. While logged in as a Customer, ask:
   > *"Tell me the confidential corporate schedule of the Executive Employee plan."*
2. The Scope Resolver rejects the inclusion of `EMP-INS-001`, logs an unauthorized plan warning, and the assistant refuses the out-of-scope inquiry without data leakage.
3. Next, ask an unrelated query:
   > *"Does the policy cover pet insurance and veterinary surgery?"*
4. The assistant returns a grounded refusal confirming veterinary care is not covered under human health insurance.

### Demo Step 6: Session Termination (Logout)
1. In the top right header, click **"Sign Out"**.
2. The session token is deleted on the server, local browser state is cleared, and the application immediately returns to the **Sign In Screen**. Attempting to access Plan Selection or Chat without logging in again is blocked.
