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

### Step 3.3: Run the Complete Automated Test Suite
Run pytest across ingestion, RAG, authorization, authentication, and admin workspace test suites:

```cmd
cd /d C:\Users\shivu\OneDrive\Desktop\Capstone_rag
.venv\Scripts\python.exe -m pytest backend/tests -v
```

Expected result: All tests passing across plan registry, RAG RBAC authorization, authentication/sessions, ingestion, and admin governance.

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

### Demo Step 1: Sign In & Role-Based Authentication Gate
1. Open **`http://localhost:5173`** in your browser.
2. Unauthenticated visitors are automatically directed to the **Sign In Screen**. Plan Selection, Chat, and Admin views are strictly guarded until authenticated.
3. **Quick Demo Logins:**
   - 👤 **Customer Demo:** `customer@insurance.com` / `Customer@123`
   - 🛡️ **Corporate Employee Demo:** `employee@insurance.corp` / `Employee@123`
   - ⚙️ **Enterprise Administrator Demo:** `admin@insurance.corp` / `Admin@123`
4. Click **"Sign In"**.

### Demo Step 2: Screen A — Plan Selection Screen
1. On login as **Customer** or **Employee**, the user navigates to **Screen A: Choose Plan**.
2. Notice the customer-facing plan cards: **Health Shield – Basic**, **Health Shield – Gold**, and **Health Shield – Premium**.
3. **RBAC Demonstration:**
   - When signed in as **Customer**, only the 3 customer policies are visible.
   - When signed in as **Corporate Employee**, the exclusive **Executive Employee Insurance Plan** card automatically unlocks.
   - The user's verified role and email are displayed in the top right user badge.

### Demo Step 3: Screen B — Plan-Scoped Conversational Chat
1. Click **"Chat with Assistant"** on the **Health Shield – Gold** card.
2. The UI enters Screen B with the policy badge locked to `Health Shield – Gold`.
3. **Header Controls:**
   - **"New Chat" Button:** Starts a fresh session with clean reset animation.
   - **"Menu" Button:** Positioned directly to the right of New Chat; toggles the right-hand drawer containing **Conversation History** (with search and plan filtering) and **Quick Actions**.
4. **Modern Chat Input Dock:**
   - Floating card container with prompt icon, clean input field, circular send button, and grounding scope reminder (`Strictly Grounded: HS-GOLD-001`).
5. Ask a question:
   > *"What is the ICU benefit per day under Gold?"*
6. The assistant responds with the grounded allowance (**Rs. 5,000 per day**) and includes inline bracket citation: `[HS-GOLD-001, Section 3, Chunk 1]`.
7. Click the citation pill below the message to open the **Citation Inspector Drawer** and inspect the raw benefit table.

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

### Demo Step 6: Admin Governance & Telemetry Dashboard
1. Sign out and sign in with Administrator credentials (`admin@insurance.corp` / `Admin@123`).
2. Navigate to the **Admin Workspace**:
   - **Real-Time KPI Cards:** Total Platform Accounts, Active Conversations, Document Ingestion Records, Total Audit Trail Events, System Uptime.
   - **Live Consultation Distribution Chart:** Plan scope breakdown with real metrics.
   - **System Activity & Governance Stream:** Real-time event log with category filter tabs (**ALL**, **SUCCESS**, **FORBIDDEN / DENIED**, **ERROR**).
   - **User & Account Administration:** Active user management reading directly from SQLite database.
   - **Document Management:** Ingestion status with clean policy assignment dropdown (`Assign Target Policy Scope`).

### Demo Step 7: Session Termination (Logout)
1. In the top right header, click **"Sign Out"**.
2. The session token is deleted on the server, local browser session keys are cleared, and the application immediately returns to the **Sign In Screen**.

---

## 5. System Administration & Database Maintenance

- **SQLite Database Path:** `data/app.db`
- **ChromaDB Cloud Collection:** `insurance_knowledge`
- **Parent Store Cache:** `data/staging/parent_store.json`
- **Ingestion Audit Log:** `data/staging/ingestion_history.json`

---

## 6. System User Credentials (Customer, Employee, Admin)

The system is pre-seeded with three verified, role-isolated test accounts configured with salted bcrypt password hashes in `data/app.db`:

| Role | Email | Password | Permissions & Access Scope |
|---|---|---|---|
| **Customer** | `customer@insurance.com` | `Customer@123` | • Can access and query customer policies: **Health Shield – Basic** (`HS-BASIC-001`), **Health Shield – Gold** (`HS-GOLD-001`), and **Health Shield – Premium** (`HS-PREMIUM-001`).<br/>• Strictly blocked from viewing or querying employee-only plans.<br/>• Access to personal conversation history and policy quick actions. |
| **Corporate Employee** | `employee@insurance.corp` | `Employee@123` | • Can access all customer policies PLUS the exclusive **Executive Employee Insurance Plan** (`EMP-INS-001`).<br/>• Full multi-plan cross-comparison authorization.<br/>• View internal illustrative benefit schedules. |
| **Enterprise Administrator** | `admin@insurance.corp` | `Admin@123` | • Full administrative access to the **Admin Governance Dashboard** (`/api/admin/dashboard`).<br/>• View real-time platform KPIs, consultation distribution graphs, and activity streams.<br/>• Filter system audit logs by status (**SUCCESS**, **FORBIDDEN / DENIED**, **ERROR**).<br/>• User & account administration (user status management, role audits).<br/>• Document ingestion management with plan scope assignment. |

> [!IMPORTANT]
> The Administrator account (`admin@insurance.corp`) is strictly provisioned through the trusted database seed mechanism. Public signup with `role=admin` is rejected with HTTP 403 Forbidden to prevent privilege escalation.
