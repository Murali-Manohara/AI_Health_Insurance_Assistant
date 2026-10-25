import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.auth_service import AuthorizationService

client = TestClient(app)

def create_authenticated_customer(plan_id="HS-GOLD-001"):
    email = f"cust_auth_{uuid.uuid4().hex[:8]}@example.com"
    signup = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "Password123!",
            "role": "customer",
            "full_name": "Test Customer"
        }
    )
    token = signup.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/eligibility/assess",
        headers=headers,
        json={
            "age": 28,
            "height_cm": 172,
            "weight_kg": 68,
            "smoker": "No",
            "alcoholic": "No",
            "pre_existing_condition": "None"
        }
    )
    client.post(
        "/api/eligibility/select-plan",
        headers=headers,
        json={"selected_plan_id": plan_id}
    )
    return headers

def create_authenticated_employee():
    email = f"emp_auth_{uuid.uuid4().hex[:8]}@insurance.corp"
    signup = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "Password123!",
            "role": "employee",
            "full_name": "Staff Employee"
        }
    )
    token = signup.json()["token"]
    return {"Authorization": f"Bearer {token}"}

def test_customer_cannot_access_employee_plan():
    """Customer role must be denied access when creating conversation for EMP-INS-001."""
    cust_headers = create_authenticated_customer("HS-GOLD-001")
    resp = client.post(
        "/api/conversations",
        headers=cust_headers,
        json={"selected_plan_id": "EMP-INS-001"}
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"].lower() or "access denied" in resp.json()["detail"].lower()

def test_employee_can_access_all_plans():
    """Employee role can access Basic, Gold, Premium, and EMP-INS-001."""
    for pid in ["HS-BASIC-001", "HS-GOLD-001", "HS-PREMIUM-001", "EMP-INS-001"]:
        assert AuthorizationService.is_plan_authorized("employee", pid) is True

    emp_headers = create_authenticated_employee()
    resp = client.post(
        "/api/conversations",
        headers=emp_headers,
        json={"selected_plan_id": "EMP-INS-001"}
    )
    assert resp.status_code == 201
    assert resp.json()["selected_plan_id"] == "EMP-INS-001"

def test_invalid_role_fails_closed():
    """Requests without token fail closed with 401 Unauthorized regardless of client header."""
    resp = client.get(
        "/api/plans",
        headers={"X-User-Role": "anonymous_hacker"}
    )
    assert resp.status_code == 401
    assert "authentication required" in resp.json()["detail"].lower()

def test_customer_cannot_leak_employee_content_in_comparison():
    """Customer asking to compare with employee plan receives an access restriction notice."""
    cust_headers = create_authenticated_customer("HS-GOLD-001")
    # Create valid Gold conversation for customer
    c_resp = client.post(
        "/api/conversations",
        headers=cust_headers,
        json={"selected_plan_id": "HS-GOLD-001"}
    )
    assert c_resp.status_code == 201
    conv_id = c_resp.json()["conversation_id"]

    # Send message asking for employee plan
    m_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=cust_headers,
        json={"query": "Compare Gold with Executive Employee Plan"}
    )
    assert m_resp.status_code == 200
    data = m_resp.json()
    assert "EMP-INS-001" in data["scope_resolution"]["denied_plans"]
    assert "EMP-INS-001" not in data["scope_resolution"]["effective_scope"]
    assert "Access Restriction Notice" in data["message"]["content"]
    # Verify no employee citation returned to customer
    for cit in data["message"]["citations"]:
        assert cit["plan_id"] != "EMP-INS-001"

def test_diagnostic_search_enforces_rbac():
    """Diagnostic search strictly restricts scope to authorized plans."""
    cust_headers = create_authenticated_customer("HS-GOLD-001")
    resp = client.post(
        "/api/retrieval/search",
        headers=cust_headers,
        json={
            "query": "ICU coverage",
            "effective_scope": ["HS-GOLD-001", "EMP-INS-001"]
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "EMP-INS-001" not in data["effective_scope"]
    for c in data["chunks"]:
        assert c["plan_id"] != "EMP-INS-001"
