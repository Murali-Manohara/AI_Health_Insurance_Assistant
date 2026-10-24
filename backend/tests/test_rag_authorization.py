import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.auth_service import AuthorizationService, UserIdentity

client = TestClient(app)

def test_customer_cannot_access_employee_plan():
    """Customer role must be denied access when creating conversation for EMP-INS-001."""
    resp = client.post(
        "/api/conversations",
        headers={"X-User-Role": "customer"},
        json={"selected_plan_id": "EMP-INS-001"}
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]

def test_employee_can_access_all_plans():
    """Employee role can access Basic, Gold, Premium, and EMP-INS-001."""
    for pid in ["HS-BASIC-001", "HS-GOLD-001", "HS-PREMIUM-001", "EMP-INS-001"]:
        assert AuthorizationService.is_plan_authorized("employee", pid) is True

    resp = client.post(
        "/api/conversations",
        headers={"X-User-Role": "employee"},
        json={"selected_plan_id": "EMP-INS-001"}
    )
    assert resp.status_code == 201
    assert resp.json()["selected_plan_id"] == "EMP-INS-001"

def test_invalid_role_fails_closed():
    """Unrecognized roles fail closed with 401 Unauthorized."""
    resp = client.get(
        "/api/plans",
        headers={"X-User-Role": "anonymous_hacker"}
    )
    assert resp.status_code == 401
    assert "Invalid or unrecognized" in resp.json()["detail"]

def test_customer_cannot_leak_employee_content_in_comparison():
    """Customer asking to compare with employee plan receives an access restriction notice."""
    # Create valid Gold conversation for customer
    c_resp = client.post(
        "/api/conversations",
        headers={"X-User-Role": "customer"},
        json={"selected_plan_id": "HS-GOLD-001"}
    )
    conv_id = c_resp.json()["conversation_id"]

    # Send message asking for employee plan
    m_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers={"X-User-Role": "customer"},
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
    resp = client.post(
        "/api/retrieval/search",
        headers={"X-User-Role": "customer"},
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
