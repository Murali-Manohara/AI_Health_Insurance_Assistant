# Data Schemas & Metadata Specifications

This document defines the data contracts, storage schemas, and API payload definitions utilized throughout the AI Insurance Assistant platform.

---

## 1. ChromaDB Flat Child Chunk Metadata Schema

ChromaDB mandates that all metadata dictionary values must be flat primitive types (`str`, `int`, `float`, `bool`). Nested lists or objects are strictly prohibited in vector stores.

```json
{
  "chunk_id": "chunk_HS-GOLD-001_sec_3_001",
  "plan_id": "HS-GOLD-001",
  "plan_name": "Health Shield – Gold",
  "plan_category": "Gold",
  "audience": "customer",
  "access_level": "customer",
  "section_number": "3",
  "section_title": "Section 3: Hospital Cash Benefit Schedule",
  "subsection_title": "Daily ICU Benefit",
  "content_type": "table",
  "parent_section_id": "HS-GOLD-001-SEC-03",
  "source_document": "health_shield_gold.pdf",
  "source_page_start": 3,
  "source_page_end": 3,
  "document_version": "1.0",
  "data_status": "verified",
  "chunk_index": 4
}
```

### Schema Rules:
- **`access_level`**: `"customer"` or `"employee"`. Used by the hybrid retrieval pre-filter to enforce RBAC.
- **`data_status`**: `"verified"` for standard health policies; `"illustrative_unverified"` for employee demo clauses.
- **`content_type`**: Distinguishes `"paragraph"`, `"table"`, and `"calculation"`.
- **`parent_section_id`**: Direct foreign key pointer to `parent_store.json`.

---

## 2. Parent Section Store Schema (`parent_store.json`)

Stores the complete, unsegmented markdown content of each section, preserving headers, clauses, and tabular matrices for RAG context expansion:

```json
{
  "parent_id": "HS-BASIC-001-SEC-03",
  "plan_id": "HS-BASIC-001",
  "section_number": "3",
  "section_title": "Section 3: Hospital Cash Benefit Schedule",
  "source_document": "health_shield_basic.pdf",
  "page_start": 2,
  "page_end": 3,
  "full_text": "## Section 3: Hospital Cash Benefit Schedule\n\nDaily allowance...",
  "markdown_tables": [
    "| Benefit | Daily Limit | Max Days |\n|---|---|---|\n| Daily Hospital Cash | Rs. 1,500 | 30 days |\n| Daily ICU Benefit | Rs. 3,000 | 15 days |"
  ],
  "token_count": 482
}
```

---

## 3. Plan Registry Schema (`GET /api/plans`)

Returned by the plans endpoint to populate Screen A cards:

```json
{
  "id": "HS-GOLD-001",
  "name": "Health Shield – Gold",
  "display_name": "Health Shield – Gold",
  "tier": "gold",
  "annual_premium_inr": 14200,
  "hospital_cash_daily_inr": 2500,
  "icu_cash_daily_inr": 5000,
  "description": "Comprehensive inpatient coverage featuring enhanced ICU benefits.",
  "is_employee_only": false,
  "highlights": [
    "Rs. 2,500/day hospital cash",
    "Rs. 5,000/day ICU benefit",
    "Enhanced Day-Care procedure limits",
    "7.5% annual claim-free increase"
  ]
}
```

---

## 4. Conversation & Message Session Schema (`conversations.json`)

Maintains server-side conversational context and turn history:

```json
{
  "c7a8b9e0-1234-5678-9abc-def012345678": {
    "conversation_id": "c7a8b9e0-1234-5678-9abc-def012345678",
    "plan_id": "HS-GOLD-001",
    "plan_name": "Health Shield – Gold",
    "role": "customer",
    "messages": [
      {
        "id": "msg_001",
        "conversation_id": "c7a8b9e0-1234-5678-9abc-def012345678",
        "role": "user",
        "content": "What is the ICU benefit per day?",
        "created_at": "2026-10-23T17:35:00Z"
      },
      {
        "id": "msg_002",
        "conversation_id": "c7a8b9e0-1234-5678-9abc-def012345678",
        "role": "assistant",
        "content": "Under Health Shield – Gold, the Daily ICU Benefit provides Rs. 5,000 per day for up to 15 days per policy year [HS-GOLD-001, Section 3, Chunk 3].\n\n*Note: All benefit statements are derived strictly from policy documents.*",
        "citations": [
          {
            "chunk_id": "chunk_HS-GOLD-001_sec_3_001",
            "plan_id": "HS-GOLD-001",
            "plan_name": "Health Shield – Gold",
            "section_number": "3",
            "section_title": "Section 3: Hospital Cash Benefit Schedule",
            "source_document": "health_shield_gold.pdf",
            "page_number": 3,
            "citation_text": "[HS-GOLD-001, Section 3, Chunk 1]",
            "parent_context": "## Section 3: Hospital Cash Benefit Schedule\n\n| Benefit | Limit |\n|---|---|\n| Daily ICU Benefit | Rs. 5,000/day |",
            "relevance_score": 0.0328
          }
        ],
        "retrieval_scope": ["HS-GOLD-001"],
        "comparison_detected": false,
        "created_at": "2026-10-23T17:35:05Z"
      }
    ],
    "created_at": "2026-10-23T17:35:00Z",
    "updated_at": "2026-10-23T17:35:05Z"
  }
}
```

---

## 5. SQLite Governance & Local Storage Schema (`data/app.db`)

Thread-safe SQLite database initialized with WAL journal mode (`PRAGMA journal_mode = WAL;`) for local storage, authenticated identity governance, and persistent chat audits.

### 5.1 `users` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `user_id` | TEXT | PRIMARY KEY | Unique user identifier (`usr_...`). |
| `email` | TEXT | UNIQUE NOT NULL COLLATE NOCASE | User email address. |
| `password_hash` | TEXT | NOT NULL | Salted bcrypt hash. Plaintext passwords never stored. |
| `requested_role` | TEXT | NOT NULL | User-selected role (`customer` or `employee`). |
| `effective_role` | TEXT | NOT NULL | Server-verified role enforced for RBAC. |
| `is_approved` | INTEGER | NOT NULL DEFAULT 1 | 1 for approved customer or verified corporate employee; 0 for pending. |
| `full_name` | TEXT | NULL | User display name. |
| `created_at` | TEXT | NOT NULL | UTC ISO-8601 registration timestamp. |

### 5.2 `sessions` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `token` | TEXT | PRIMARY KEY | Secure random session token (`sess_...`). |
| `user_id` | TEXT | NOT NULL, FK to `users` | Foreign key referencing user record. |
| `role` | TEXT | NOT NULL | Active role bound to session. |
| `created_at` | TEXT | NOT NULL | Creation timestamp. |
| `expires_at` | TEXT | NOT NULL | Expiry timestamp (24-hour default validity). |

### 5.3 `conversations` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `conversation_id` | TEXT | PRIMARY KEY | Unique conversation identifier (`conv_...`). |
| `user_id` | TEXT | NOT NULL | Owner user identifier. |
| `role` | TEXT | NOT NULL | Role bound to conversation. |
| `selected_plan_id` | TEXT | NOT NULL | Policy plan boundary (`HS-BASIC-001`, `HS-GOLD-001`, etc.). |
| `created_at` | TEXT | NOT NULL | Session creation timestamp. |
| `updated_at` | TEXT | NOT NULL | Last activity timestamp. |

### 5.4 `messages` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `message_id` | TEXT | PRIMARY KEY | Unique message identifier (`msg_...`). |
| `conversation_id` | TEXT | NOT NULL, FK to `conversations` | Owning conversation session. |
| `role` | TEXT | NOT NULL | Message sender: `"user"` or `"assistant"`. |
| `content` | TEXT | NOT NULL | Message text. |
| `citations_json` | TEXT | DEFAULT '[]' | Serialized array of grounded policy citations. |
| `effective_scope_json` | TEXT | DEFAULT '[]' | Retrieved plans scope list. |
| `is_comparison` | INTEGER | DEFAULT 0 | 1 if multi-plan comparison query. |
| `is_clarification` | INTEGER | DEFAULT 0 | 1 if clarification response. |
| `contains_unverified_notice` | INTEGER | DEFAULT 0 | 1 if illustrative employee notice was included. |
| `timestamp` | TEXT | NOT NULL | ISO-8601 timestamp. |

### 5.5 `profiles` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `user_id` | TEXT | PRIMARY KEY, FK to `users` | User identifier. |
| `email` | TEXT | NOT NULL | User contact email. |
| `role` | TEXT | NOT NULL | Current active role. |
| `governance_status` | TEXT | NOT NULL | Account status: `"active"`, `"verified_employee"`, `"pending_verification"`. |
| `last_login` | TEXT | NULL | Most recent session login timestamp. |

