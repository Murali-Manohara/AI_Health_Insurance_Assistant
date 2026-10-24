import sqlite3
import uuid
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path
import bcrypt
from backend.app.core.config import settings
from backend.app.core.logging_config import logger

DB_PATH: Path = settings.DATA_DIR / "app.db"

class SQLiteManager:
    """
    Thread-safe SQLite database manager for local data governance,
    including authentication (users, bcrypt password hashes, active sessions),
    user profiles, and conversation/message history.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
        self._seed_default_accounts()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_tables(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    requested_role TEXT NOT NULL,
                    effective_role TEXT NOT NULL,
                    is_approved INTEGER NOT NULL DEFAULT 1,
                    full_name TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    selected_plan_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    citations_json TEXT DEFAULT '[]',
                    effective_scope_json TEXT DEFAULT '[]',
                    is_comparison INTEGER DEFAULT 0,
                    is_clarification INTEGER DEFAULT 0,
                    contains_unverified_notice INTEGER DEFAULT 0,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS profiles (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    role TEXT NOT NULL,
                    governance_status TEXT NOT NULL DEFAULT 'active',
                    last_login TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
                CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);
                CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);
            """)
            conn.commit()

    def _seed_default_accounts(self) -> None:
        """Seed default verified demo accounts if database is empty."""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                # Default authorized employee
                cur.execute("SELECT user_id FROM users WHERE email = 'employee@insurance.corp'")
                if not cur.fetchone():
                    salt = bcrypt.gensalt()
                    emp_hash = bcrypt.hashpw(b"Employee@123", salt).decode("utf-8")
                    emp_id = "user_emp_demo"
                    now = datetime.now(timezone.utc).isoformat()
                    cur.execute("""
                        INSERT INTO users (user_id, email, password_hash, requested_role, effective_role, is_approved, full_name, created_at)
                        VALUES (?, ?, ?, 'employee', 'employee', 1, 'Authorized Employee Staff', ?)
                    """, (emp_id, "employee@insurance.corp", emp_hash, now))
                    cur.execute("""
                        INSERT OR REPLACE INTO profiles (user_id, email, role, governance_status, last_login)
                        VALUES (?, 'employee@insurance.corp', 'employee', 'verified_employee', ?)
                    """, (emp_id, now))

                # Default customer
                cur.execute("SELECT user_id FROM users WHERE email = 'customer@insurance.com'")
                if not cur.fetchone():
                    salt = bcrypt.gensalt()
                    cust_hash = bcrypt.hashpw(b"Customer@123", salt).decode("utf-8")
                    cust_id = "user_cust_demo"
                    now = datetime.now(timezone.utc).isoformat()
                    cur.execute("""
                        INSERT INTO users (user_id, email, password_hash, requested_role, effective_role, is_approved, full_name, created_at)
                        VALUES (?, ?, ?, 'customer', 'customer', 1, 'Policy Holder Customer', ?)
                    """, (cust_id, "customer@insurance.com", cust_hash, now))
                    cur.execute("""
                        INSERT OR REPLACE INTO profiles (user_id, email, role, governance_status, last_login)
                        VALUES (?, 'customer@insurance.com', 'customer', 'active_customer', ?)
                    """, (cust_id, now))

                conn.commit()
        except Exception as e:
            logger.error(f"Error seeding default accounts: {e}")

    # ==================== USER MANAGEMENT ====================

    def create_user(
        self,
        email: str,
        password_hash: str,
        requested_role: str,
        effective_role: str,
        is_approved: int,
        full_name: str
    ) -> dict:
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO users (user_id, email, password_hash, requested_role, effective_role, is_approved, full_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, email.strip().lower(), password_hash, requested_role, effective_role, is_approved, full_name, now))
            
            cur.execute("""
                INSERT INTO profiles (user_id, email, role, governance_status, last_login)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, email.strip().lower(), effective_role, 'active' if is_approved else 'pending_verification', now))
            
            conn.commit()
            return {
                "user_id": user_id,
                "email": email.strip().lower(),
                "role": effective_role,
                "requested_role": requested_role,
                "is_approved": is_approved,
                "full_name": full_name,
                "created_at": now
            }

    def get_user_by_email(self, email: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip().lower(),))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None

    # ==================== SESSION MANAGEMENT ====================

    def create_session(self, user_id: str, role: str, duration_hours: int = 24) -> str:
        token = f"sess_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(hours=duration_hours)).isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sessions (token, user_id, role, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (token, user_id, role, now.isoformat(), expires_at))
            
            # Update profile last_login
            cur.execute("UPDATE profiles SET last_login = ? WHERE user_id = ?", (now.isoformat(), user_id))
            conn.commit()
        return token

    def get_session(self, token: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.token, s.user_id, s.role, s.created_at, s.expires_at,
                       u.email, u.full_name, u.effective_role, u.is_approved
                FROM sessions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.token = ?
            """, (token,))
            row = cur.fetchone()
            if not row:
                return None
            data = dict(row)
            # Check expiration
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.now(timezone.utc) > expires_at:
                # Expired -> delete
                cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                return None
            return data

    def delete_session(self, token: str) -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return cur.rowcount > 0

    # ==================== CONVERSATIONS & CHAT HISTORY ====================

    def save_conversation(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        selected_plan_id: str,
        created_at: str,
        updated_at: str
    ) -> None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO conversations (conversation_id, user_id, role, selected_plan_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (conversation_id, user_id, role, selected_plan_id, created_at, updated_at))
            conn.commit()

    def get_conversation(self, conversation_id: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_conversations_for_user(self, user_id: str) -> list[dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
            return [dict(r) for r in cur.fetchall()]

    def save_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        citations_json: str,
        effective_scope_json: str,
        is_comparison: bool,
        is_clarification: bool,
        contains_unverified_notice: bool,
        timestamp: str
    ) -> None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO messages (
                    message_id, conversation_id, role, content, citations_json,
                    effective_scope_json, is_comparison, is_clarification,
                    contains_unverified_notice, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message_id, conversation_id, role, content, citations_json,
                effective_scope_json, int(is_comparison), int(is_clarification),
                int(contains_unverified_notice), timestamp
            ))
            # Touch conversation updated_at
            cur.execute("UPDATE conversations SET updated_at = ? WHERE conversation_id = ?", (timestamp, conversation_id))
            conn.commit()

    def get_messages_for_conversation(self, conversation_id: str) -> list[dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC", (conversation_id,))
            rows = cur.fetchall()
            messages = []
            for r in rows:
                m = dict(r)
                m["citations"] = json.loads(m.get("citations_json") or "[]")
                m["effective_scope"] = json.loads(m.get("effective_scope_json") or "[]")
                m["is_comparison"] = bool(m.get("is_comparison"))
                m["is_clarification"] = bool(m.get("is_clarification"))
                m["contains_unverified_notice"] = bool(m.get("contains_unverified_notice"))
                messages.append(m)
            return messages

# Global singleton
sqlite_db = SQLiteManager()
