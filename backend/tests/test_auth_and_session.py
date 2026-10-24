import pytest
import uuid
import bcrypt
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.sqlite_manager import sqlite_db
from backend.app.services.auth_service import hash_password, verify_password

client = TestClient(app)

def test_password_hashing_and_verification():
    """Passwords must be hashed using bcrypt and never stored in plaintext."""
    raw = "SecureSecret123!"
    hashed = hash_password(raw)
    assert raw != hashed
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

def test_signup_with_valid_data():
    """Signup creates a valid user in SQLite, generates a session token, and returns user payload."""
    email = f"test_user_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "Password123!",
            "role": "customer",
            "full_name": "Test Customer"
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert data["user"]["email"] == email.lower()
    assert data["user"]["role"] == "customer"
    assert data["user"]["is_approved"] is True

    # Verify directly in SQLite that plaintext password was NOT stored
    db_user = sqlite_db.get_user_by_email(email)
    assert db_user is not None
    assert db_user["password_hash"] != "Password123!"
    assert bcrypt.checkpw(b"Password123!", db_user["password_hash"].encode("utf-8"))

def test_signup_with_invalid_email():
    """Signup rejects invalid email format."""
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": "not-a-valid-email",
            "password": "Password123!",
            "role": "customer"
        }
    )
    assert resp.status_code == 422

def test_signup_with_short_password():
    """Signup enforces minimum password length (8 chars)."""
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": "valid_email@example.com",
            "password": "short",
            "role": "customer"
        }
    )
    assert resp.status_code == 422

def test_signup_duplicate_account_rejected():
    """Registering with an already existing email returns 400 Bad Request."""
    email = f"dup_user_{uuid.uuid4().hex[:8]}@example.com"
    # First registration
    client.post(
        "/api/auth/signup",
        json={"email": email, "password": "Password123!", "role": "customer"}
    )
    # Duplicate attempt
    resp2 = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "AnotherPassword123!", "role": "customer"}
    )
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]

def test_employee_signup_protection():
    """
    Self-selecting Employee role does NOT automatically grant employee access
    unless using a verified corporate domain.
    """
    # 1. Non-corporate email requesting employee
    public_email = f"applicant_{uuid.uuid4().hex[:8]}@gmail.com"
    resp = client.post(
        "/api/auth/signup",
        json={"email": public_email, "password": "Password123!", "role": "employee"}
    )
    assert resp.status_code == 201
    data = resp.json()
    # Effective role is demoted to customer / unapproved
    assert data["user"]["role"] == "customer"
    assert data["user"]["is_approved"] is False
    assert "pending administrative verification" in data["message"]

    # 2. Corporate email requesting employee
    corp_email = f"staff_{uuid.uuid4().hex[:8]}@insurance.corp"
    resp_corp = client.post(
        "/api/auth/signup",
        json={"email": corp_email, "password": "Password123!", "role": "employee"}
    )
    assert resp_corp.status_code == 201
    data_corp = resp_corp.json()
    assert data_corp["user"]["role"] == "employee"
    assert data_corp["user"]["is_approved"] is True

def test_login_with_valid_and_invalid_credentials():
    """Login verifies credentials server-side and issues token."""
    email = f"login_test_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/auth/signup",
        json={"email": email, "password": "CorrectPassword123!", "role": "customer"}
    )

    # Valid login
    resp_valid = client.post(
        "/api/auth/login",
        json={"email": email, "password": "CorrectPassword123!"}
    )
    assert resp_valid.status_code == 200
    valid_data = resp_valid.json()
    assert "token" in valid_data
    assert valid_data["user"]["email"] == email

    # Invalid password
    resp_bad_pw = client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPassword!"}
    )
    assert resp_bad_pw.status_code == 401
    assert "Invalid email or password" in resp_bad_pw.json()["detail"]

    # Non-existent email
    resp_bad_email = client.post(
        "/api/auth/login",
        json={"email": "non_existent@example.com", "password": "Password123!"}
    )
    assert resp_bad_email.status_code == 401
    assert "Invalid email or password" in resp_bad_email.json()["detail"]

def test_accessing_protected_endpoints_without_authentication():
    """Accessing protected endpoints with neither token nor role header returns 401."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]

def test_accessing_protected_endpoints_with_invalid_or_expired_token():
    """Accessing protected endpoints with an invalid token returns 401."""
    resp = client.get(
        "/api/plans",
        headers={"Authorization": "Bearer sess_invalid_fake_token_12345"}
    )
    assert resp.status_code == 401
    assert "Invalid or expired" in resp.json()["detail"]

def test_customer_cannot_spoof_employee_role_via_header():
    """
    When authenticated as customer with a token, passing 'X-User-Role: employee'
    must NOT grant employee access because the backend derives role from SQLite.
    """
    # 1. Register customer
    cust_email = f"honest_customer_{uuid.uuid4().hex[:8]}@example.com"
    reg_resp = client.post(
        "/api/auth/signup",
        json={"email": cust_email, "password": "Password123!", "role": "customer"}
    )
    cust_token = reg_resp.json()["token"]

    # 2. Try to view plans with token AND spoofed X-User-Role: employee header
    plans_resp = client.get(
        "/api/plans",
        headers={
            "Authorization": f"Bearer {cust_token}",
            "X-User-Role": "employee"  # Spoofing attempt
        }
    )
    assert plans_resp.status_code == 200
    plan_ids = [p["plan_id"] for p in plans_resp.json()["plans"]]
    # EMP-INS-001 must NOT be in the list!
    assert "EMP-INS-001" not in plan_ids

    # 3. Try to create conversation for EMP-INS-001 with customer token + spoofed header
    conv_resp = client.post(
        "/api/conversations",
        headers={
            "Authorization": f"Bearer {cust_token}",
            "X-User-Role": "employee"
        },
        json={"selected_plan_id": "EMP-INS-001"}
    )
    assert conv_resp.status_code == 403
    assert "Access denied" in conv_resp.json()["detail"]

def test_authorized_employee_access_with_token():
    """Authorized employee with valid token can access all 4 plans including EMP-INS-001."""
    # Login with seeded employee
    emp_resp = client.post(
        "/api/auth/login",
        json={"email": "employee@insurance.corp", "password": "Employee@123"}
    )
    assert emp_resp.status_code == 200
    emp_token = emp_resp.json()["token"]

    # List plans
    plans_resp = client.get(
        "/api/plans",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert plans_resp.status_code == 200
    plan_ids = [p["plan_id"] for p in plans_resp.json()["plans"]]
    assert "EMP-INS-001" in plan_ids
    assert "HS-BASIC-001" in plan_ids
    assert "HS-GOLD-001" in plan_ids
    assert "HS-PREMIUM-001" in plan_ids

    # Create employee conversation
    conv_resp = client.post(
        "/api/conversations",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"selected_plan_id": "EMP-INS-001"}
    )
    assert conv_resp.status_code == 201
    assert conv_resp.json()["selected_plan_id"] == "EMP-INS-001"

def test_logout_invalidates_session():
    """Logout invalidates the session token in SQLite, denying subsequent requests."""
    # Login
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "customer@insurance.com", "password": "Customer@123"}
    )
    token = login_resp.json()["token"]

    # Verify session works
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 200

    # Logout
    logout_resp = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout_resp.status_code == 200

    # Session must now be rejected
    me_after = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_after.status_code == 401
