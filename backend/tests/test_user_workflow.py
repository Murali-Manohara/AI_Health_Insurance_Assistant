import pytest
import bcrypt
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.sqlite_manager import sqlite_db
from backend.app.services.auth_service import verify_password

client = TestClient(app)

def test_demo_accounts_provisioning_and_login():
    """
    Section 4 & 13.A:
    Verify that Shivu (Customer), Murali (Employee), and Administrator (Admin)
    are provisioned correctly with the requested demo credentials.
    """
    # Explicit provisioning
    results = sqlite_db.provision_demo_accounts(force_reconcile=True)
    assert "shivu@gmail.com" in results
    assert "murali@gmail.com" in results
    assert "admin@gmail.com" in results

    # 1. Customer: Shivu
    cust_user = sqlite_db.get_user_by_email("shivu@gmail.com")
    assert cust_user is not None
    assert cust_user["effective_role"] == "customer"
    assert cust_user["full_name"] == "Shivu"
    assert cust_user["is_approved"] == 1
    assert verify_password("12345678", cust_user["password_hash"]) is True
    # Password must be hashed, never plaintext
    assert cust_user["password_hash"] != "12345678"

    # Login via API
    resp = client.post("/api/auth/login", json={"email": "shivu@gmail.com", "password": "12345678"})
    assert resp.status_code == 200
    cust_token = resp.json()["token"]
    assert cust_token is not None

    # 2. Employee: Murali
    emp_user = sqlite_db.get_user_by_email("murali@gmail.com")
    assert emp_user is not None
    assert emp_user["effective_role"] == "employee"
    assert emp_user["full_name"] == "Murali"
    assert emp_user["is_approved"] == 1
    assert verify_password("12345678", emp_user["password_hash"]) is True
    assert emp_user["password_hash"] != "12345678"

    resp = client.post("/api/auth/login", json={"email": "murali@gmail.com", "password": "12345678"})
    assert resp.status_code == 200
    emp_token = resp.json()["token"]
    assert emp_token is not None

    # 3. Admin: Administrator
    admin_user = sqlite_db.get_user_by_email("admin@gmail.com")
    assert admin_user is not None
    assert admin_user["effective_role"] == "admin"
    assert admin_user["full_name"] == "Administrator"
    assert admin_user["is_approved"] == 1
    assert verify_password("admin@123", admin_user["password_hash"]) is True
    assert admin_user["password_hash"] != "admin@123"

    resp = client.post("/api/auth/login", json={"email": "admin@gmail.com", "password": "admin@123"})
    assert resp.status_code == 200
    admin_token = resp.json()["token"]
    assert admin_token is not None

    # 4. Verify repeated provisioning is idempotent and does not create duplicates
    repeat_results = sqlite_db.provision_demo_accounts(force_reconcile=False)
    assert repeat_results["shivu@gmail.com"] == "EXISTS"
    assert repeat_results["murali@gmail.com"] == "EXISTS"
    assert repeat_results["admin@gmail.com"] == "EXISTS"

def test_public_signup_cannot_create_admin_or_privileged_employee():
    """
    Section 4 & 13.A:
    Public registration cannot create an Admin account or grant unauthorized employee privileges.
    """
    # 1. Admin signup rejected
    resp = client.post(
        "/api/auth/signup",
        json={"email": "hacker_admin@example.com", "password": "password123", "role": "admin", "full_name": "Fake Admin"}
    )
    assert resp.status_code in (403, 422)

    # 2. Public employee signup without corporate domain does not grant employee role
    resp = client.post(
        "/api/auth/signup",
        json={"email": "public_person@gmail.com", "password": "password123", "role": "employee", "full_name": "Public Person"}
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "customer"

def test_profile_persistence_for_all_three_roles():
    """
    Section 5 & 13.B:
    Verify each role sees the correct persisted profile fields via /api/auth/me.
    """
    # 1. Customer Profile
    login_cust = client.post("/api/auth/login", json={"email": "shivu@gmail.com", "password": "12345678"}).json()
    token_cust = login_cust["token"]

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_cust}"})
    assert resp.status_code == 200
    p = resp.json()
    assert p["email"] == "shivu@gmail.com"
    assert p["role"] == "customer"
    assert p["full_name"] == "Shivu"
    assert p["account_status"] == "ACTIVE"
    assert "eligibility_status" in p
    assert "authorized_plans" in p
    assert "HS-BASIC-001" in p["authorized_plans"]
    assert "EMP-INS-001" not in p["authorized_plans"]

    # 2. Employee Profile
    login_emp = client.post("/api/auth/login", json={"email": "murali@gmail.com", "password": "12345678"}).json()
    token_emp = login_emp["token"]

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_emp}"})
    assert resp.status_code == 200
    p_emp = resp.json()
    assert p_emp["email"] == "murali@gmail.com"
    assert p_emp["role"] == "employee"
    assert p_emp["full_name"] == "Murali"
    assert "EMP-INS-001" in p_emp["authorized_plans"]

    # 3. Admin Profile
    login_admin = client.post("/api/auth/login", json={"email": "admin@gmail.com", "password": "admin@123"}).json()
    token_admin = login_admin["token"]

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_admin}"})
    assert resp.status_code == 200
    p_admin = resp.json()
    assert p_admin["email"] == "admin@gmail.com"
    assert p_admin["role"] == "admin"
    assert p_admin["full_name"] == "Administrator"

    # 4. User cannot access without valid session
    bad_resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_token"})
    assert bad_resp.status_code == 401

def test_one_time_eligibility_enforcement():
    """
    Section 6 & 13.C:
    Verify that an eligibility assessment can only be completed once per user.
    Second submission returns existing saved assessment without re-running model.
    """
    # Customer login
    login_cust = client.post("/api/auth/login", json={"email": "shivu@gmail.com", "password": "12345678"}).json()
    token = login_cust["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # First assessment: valid inputs
    eval_input_1 = {
        "age": 28,
        "height_cm": 175.0,
        "weight_kg": 70.0,
        "smoker": "No",
        "alcoholic": "No",
        "pre_existing_condition": "None"
    }
    resp1 = client.post("/api/eligibility/assess", json=eval_input_1, headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    asmt_id_1 = data1["assessment_id"]
    outcome_1 = data1["outcome"]
    assert outcome_1 == "ELIGIBLE"

    # Verify assessment persisted in DB
    saved_asmt = sqlite_db.get_completed_assessment_for_user(login_cust["user"]["user_id"])
    assert saved_asmt is not None
    assert saved_asmt["assessment_id"] == asmt_id_1
    assert saved_asmt["status"] == "COMPLETED"

    # Second assessment attempt with different values (e.g. smoking and conditions)
    eval_input_2 = {
        "age": 60,
        "height_cm": 150.0,
        "weight_kg": 110.0,
        "smoker": "Yes",
        "alcoholic": "Yes",
        "pre_existing_condition": "Heart_Disease"
    }
    resp2 = client.post("/api/eligibility/assess", json=eval_input_2, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Must return the ORIGINAL assessment result!
    assert data2["assessment_id"] == asmt_id_1
    assert data2["outcome"] == outcome_1
    assert data2.get("already_completed") is True

    # Check that profile reflects the completed assessment
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.json()["eligibility_status"] == "COMPLETED"
    assert me_resp.json()["eligibility_outcome"] == "ELIGIBLE"

def test_plan_selection_and_role_authorization():
    """
    Section 7 & 13.D:
    Customer can select customer plans (Basic, Gold, Premium) but NOT employee plan.
    Employee can select employee plan.
    """
    # Customer tokens
    login_cust = client.post("/api/auth/login", json={"email": "shivu@gmail.com", "password": "12345678"}).json()
    headers_cust = {"Authorization": f"Bearer {login_cust['token']}"}

    # 1. Customer attempts to select employee-exclusive plan: MUST BE REJECTED (403)
    resp_bad = client.post("/api/eligibility/select-plan", json={"selected_plan_id": "EMP-INS-001"}, headers=headers_cust)
    assert resp_bad.status_code == 403

    # 2. Customer selects valid customer plan (HS-GOLD-001)
    resp_ok = client.post("/api/eligibility/select-plan", json={"selected_plan_id": "HS-GOLD-001"}, headers=headers_cust)
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert data["selected_plan_id"] == "HS-GOLD-001"
    assert data["status"] == "ACTIVE"

    # Verify selection persisted in database
    active_sel = sqlite_db.get_active_plan_selection_for_user(login_cust["user"]["user_id"])
    assert active_sel is not None
    assert active_sel["selected_plan_id"] == "HS-GOLD-001"

    # Verify reflected in customer profile
    me_resp = client.get("/api/auth/me", headers=headers_cust)
    assert me_resp.json()["selected_plan_id"] == "HS-GOLD-001"

    # 3. Employee workflow
    login_emp = client.post("/api/auth/login", json={"email": "murali@gmail.com", "password": "12345678"}).json()
    headers_emp = {"Authorization": f"Bearer {login_emp['token']}"}

    # Employee performs one-time assessment
    resp_emp_asmt = client.post(
        "/api/eligibility/assess",
        json={"age": 35, "height_cm": 178, "weight_kg": 75, "smoker": "No", "alcoholic": "No", "pre_existing_condition": "None"},
        headers=headers_emp
    )
    assert resp_emp_asmt.status_code == 200

    # Employee selects EMP-INS-001
    resp_emp_sel = client.post("/api/eligibility/select-plan", json={"selected_plan_id": "EMP-INS-001"}, headers=headers_emp)
    assert resp_emp_sel.status_code == 200
    assert resp_emp_sel.json()["selected_plan_id"] == "EMP-INS-001"

def test_customer_confirmation_workflow():
    """
    Section 8 & 13.E:
    Customer can confirm selected plan.
    Employee cannot confirm.
    Confirmation is idempotent and persists in profile.
    """
    # Customer login
    login_cust = client.post("/api/auth/login", json={"email": "shivu@gmail.com", "password": "12345678"}).json()
    headers_cust = {"Authorization": f"Bearer {login_cust['token']}"}

    # 1. Customer confirms selected plan (HS-GOLD-001)
    conf_resp = client.post("/api/eligibility/confirm-plan", json={"plan_id": "HS-GOLD-001"}, headers=headers_cust)
    assert conf_resp.status_code == 200
    conf_data = conf_resp.json()
    assert conf_data["status"] == "CONFIRMED"
    assert conf_data["plan_id"] == "HS-GOLD-001"
    assert "Agent will contact you soon for document verification" in conf_data["message"]
    assert conf_data["confirmed_at"] is not None

    # 2. Confirmation appears correctly in customer profile
    me_resp = client.get("/api/auth/me", headers=headers_cust)
    me_data = me_resp.json()
    assert me_data["is_confirmed"] is True
    assert me_data["confirmation_status"] == "CONFIRMED"
    assert me_data["confirmed_at"] == conf_data["confirmed_at"]

    # 3. Duplicate confirmation returns existing persisted confirmation without error
    repeat_conf = client.post("/api/eligibility/confirm-plan", json={"plan_id": "HS-GOLD-001"}, headers=headers_cust)
    assert repeat_conf.status_code == 200
    assert repeat_conf.json()["selection_id"] == conf_data["selection_id"]

    # 4. Confirmation of unselected plan fails
    wrong_plan_conf = client.post("/api/eligibility/confirm-plan", json={"plan_id": "HS-BASIC-001"}, headers=headers_cust)
    assert wrong_plan_conf.status_code == 400

    # 5. Employee confirms their active selected plan:
    login_emp = client.post("/api/auth/login", json={"email": "murali@gmail.com", "password": "12345678"}).json()
    headers_emp = {"Authorization": f"Bearer {login_emp['token']}"}
    emp_conf = client.post("/api/eligibility/confirm-plan", json={"plan_id": "EMP-INS-001"}, headers=headers_emp)
    assert emp_conf.status_code == 200
    assert emp_conf.json()["status"] == "CONFIRMED"

    # 6. Admin cannot call customer confirmation endpoint: MUST BE 403 FORBIDDEN
    login_admin = client.post("/api/auth/login", json={"email": "admin@gmail.com", "password": "admin@123"}).json()
    headers_admin = {"Authorization": f"Bearer {login_admin['token']}"}
    admin_conf = client.post("/api/eligibility/confirm-plan", json={"plan_id": "HS-GOLD-001"}, headers=headers_admin)
    assert admin_conf.status_code == 403
