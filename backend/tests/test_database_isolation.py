import pytest
import sqlite3
from pathlib import Path
from backend.app.db.sqlite_manager import sqlite_db, DB_PATH, SQLiteManager

def test_database_is_isolated_from_runtime():
    """Verify tests run against an isolated test database, NOT data/app.db."""
    runtime_path = Path(DB_PATH).resolve()
    current_test_db = Path(sqlite_db.db_path).resolve()
    assert current_test_db != runtime_path, "Tests must never execute directly against data/app.db!"
    assert "isolated_test_db" in str(current_test_db) or "test" in current_test_db.name

def test_runtime_database_access_fails_safely_during_tests():
    """Verify that any test attempt to connect directly to data/app.db triggers a safety RuntimeError."""
    unsafe_manager = SQLiteManager.__new__(SQLiteManager)
    unsafe_manager.db_path = DB_PATH

    with pytest.raises(RuntimeError) as exc_info:
        unsafe_manager._get_connection()
    
    assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)
    assert "All tests must execute against an isolated test database" in str(exc_info.value)

def test_test_record_creation_does_not_pollute_runtime_database():
    """Verify inserting a test account only modifies the isolated test database, leaving data/app.db untouched."""
    # Count rows in runtime database directly using read-only mode
    runtime_conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cur = runtime_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users;")
    runtime_count_before = cur.fetchone()[0]
    runtime_conn.close()

    # Create a user in the isolated test database
    sqlite_db.create_user(
        email="isolation_check@test.com",
        password_hash="test_hash_123",
        requested_role="customer",
        effective_role="customer",
        is_approved=1,
        full_name="Isolation Tester"
    )

    # Verify user exists in isolated test DB
    test_user = sqlite_db.get_user_by_email("isolation_check@test.com")
    assert test_user is not None
    assert test_user["email"] == "isolation_check@test.com"

    # Verify runtime database count did NOT change
    runtime_conn2 = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cur2 = runtime_conn2.cursor()
    cur2.execute("SELECT COUNT(*) FROM users;")
    runtime_count_after = cur2.fetchone()[0]
    runtime_conn2.close()

    assert runtime_count_before == runtime_count_after, "Runtime database users count increased during test!"
