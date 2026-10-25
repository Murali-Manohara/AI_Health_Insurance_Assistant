import os
import sys
from pathlib import Path

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import pytest
from backend.app.db.sqlite_manager import sqlite_db, DB_PATH

@pytest.fixture(scope="session", autouse=True)
def isolate_test_database(tmp_path_factory):
    """
    Guarantees strict test isolation.
    1. Creates an isolated temporary SQLite database for the test run.
    2. Rebinds sqlite_db to the test database.
    3. Verifies that data/app.db is NEVER modified during tests.
    """
    # Snapshot runtime DB metadata for safety verification
    runtime_db_path = Path(DB_PATH).resolve()
    initial_runtime_size = runtime_db_path.stat().st_size if runtime_db_path.exists() else 0
    initial_runtime_mtime = runtime_db_path.stat().st_mtime if runtime_db_path.exists() else 0

    # Create temporary isolated test database
    temp_dir = tmp_path_factory.mktemp("isolated_test_db")
    test_db_path = temp_dir / "test_app.db"

    # Rebind global sqlite_db to test database
    sqlite_db.rebind_db(test_db_path)

    yield test_db_path

    # Teardown & Verification: Ensure runtime DB was never touched
    if runtime_db_path.exists():
        final_runtime_size = runtime_db_path.stat().st_size
        final_runtime_mtime = runtime_db_path.stat().st_mtime
        assert initial_runtime_size == final_runtime_size, (
            f"SAFETY FAILURE: Runtime database size changed from {initial_runtime_size} to {final_runtime_size} during test execution!"
        )
        assert initial_runtime_mtime == final_runtime_mtime, (
            f"SAFETY FAILURE: Runtime database mtime changed during test execution! Last modified: {final_runtime_mtime}"
        )

    # Rebind back to runtime DB upon session conclusion
    sqlite_db.db_path = runtime_db_path
