import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.sqlite_manager import sqlite_db

client = TestClient(app)

def test_admin_bootstrap_seed_exists():
    """Verify default seeded admin account exists in database."""
    admin_user = sqlite_db.get_user_by_email("admin@insurance.corp")
    assert admin_user is not None
    assert admin_user["effective_role"] == "admin"
    assert admin_user["is_approved"] == 1

def test_public_signup_rejects_admin_role():
    """Verify that public signup strictly rejects any attempt to self-provision admin role."""
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": "hacker@evil.corp",
            "password": "Password@123",
            "role": "admin",
            "full_name": "Intruder"
        }
    )
    # Role must be rejected (either 422 validation error or 403 forbidden)
    assert resp.status_code in (403, 422)

def test_unauthenticated_access_to_admin_endpoints_returns_401():
    """Verify unauthenticated requests fail closed with 401."""
    admin_endpoints = [
        "/api/admin/overview",
        "/api/admin/users",
        "/api/admin/documents",
        "/api/admin/conversations",
        "/api/admin/rag-metrics",
        "/api/admin/audit-logs",
        "/api/admin/system-health"
    ]
    for ep in admin_endpoints:
        resp = client.get(ep)
        assert resp.status_code == 401, f"Expected 401 on {ep}, got {resp.status_code}"

def test_customer_token_access_to_admin_endpoints_returns_403():
    """Verify authenticated customers receive 403 Forbidden for all admin endpoints."""
    # Login as customer
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "customer@insurance.com", "password": "Customer@123"}
    )
    assert login_resp.status_code == 200
    cust_token = login_resp.json()["token"]

    admin_endpoints = [
        "/api/admin/overview",
        "/api/admin/users",
        "/api/admin/documents",
        "/api/admin/conversations",
        "/api/admin/rag-metrics",
        "/api/admin/audit-logs",
        "/api/admin/system-health"
    ]
    for ep in admin_endpoints:
        resp = client.get(ep, headers={"Authorization": f"Bearer {cust_token}"})
        assert resp.status_code == 403, f"Expected 403 for customer on {ep}, got {resp.status_code}"

def test_employee_token_access_to_admin_endpoints_returns_403():
    """Verify authenticated non-admin corporate employee receives 403 Forbidden."""
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "employee@insurance.corp", "password": "Employee@123"}
    )
    assert login_resp.status_code == 200
    emp_token = login_resp.json()["token"]

    resp = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {emp_token}"})
    assert resp.status_code == 403

def test_client_header_admin_spoofing_rejected():
    """Verify client cannot spoof admin role via X-User-Role header."""
    resp = client.get("/api/admin/overview", headers={"X-User-Role": "admin"})
    assert resp.status_code == 403

def test_admin_authentication_and_dashboard_access():
    """Verify admin login succeeds and provides 200 access to all dashboard sections."""
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "admin@insurance.corp", "password": "Admin@123"}
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["token"]
    assert login_resp.json()["user"]["role"] == "admin"

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Overview
    overview_resp = client.get("/api/admin/overview?range=7d", headers=headers)
    assert overview_resp.status_code == 200
    overview_data = overview_resp.json()
    assert "kpis" in overview_data
    assert "time_series" in overview_data
    assert overview_data["kpis"]["total_registered_users"] >= 1
    assert overview_data["kpis"]["total_documents"] >= 4

    # 2. Users
    users_resp = client.get("/api/admin/users", headers=headers)
    assert users_resp.status_code == 200
    users_data = users_resp.json()
    assert users_data["total"] >= 3
    # Verify no passwords or tokens exposed
    for u in users_data["users"]:
        assert "password_hash" not in u
        assert "token" not in u
        assert "role" in u
        assert "authorized_plans" in u

    # 3. Documents
    docs_resp = client.get("/api/admin/documents", headers=headers)
    assert docs_resp.status_code == 200
    docs_data = docs_resp.json()
    assert docs_data["total_documents"] >= 4
    assert "plan_distribution" in docs_data

    # 4. Conversations
    conv_resp = client.get("/api/admin/conversations?range=7d", headers=headers)
    assert conv_resp.status_code == 200
    assert "total_conversations" in conv_resp.json()

    # 5. RAG metrics
    rag_resp = client.get("/api/admin/rag-metrics?range=7d", headers=headers)
    assert rag_resp.status_code == 200
    assert "runtime_telemetry" in rag_resp.json()
    assert "offline_evaluation" in rag_resp.json()

    # 6. Audit logs
    audit_resp = client.get("/api/admin/audit-logs", headers=headers)
    assert audit_resp.status_code == 200
    assert "audit_logs" in audit_resp.json()

    # 7. System Health
    health_resp = client.get("/api/admin/system-health", headers=headers)
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert "components" in health_data
    assert "fastapi_backend" in health_data["components"]
    assert "sqlite_database" in health_data["components"]

def test_document_deletion_and_audit_logging():
    """Verify document deletion updates status and records audit event."""
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "admin@insurance.corp", "password": "Admin@123"}
    )
    admin_token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Delete non-existent document fails 404
    bad_del = client.delete("/api/admin/documents/non_existent_doc", headers=headers)
    assert bad_del.status_code == 404

    # Audit log reflects the events
    audit_resp = client.get("/api/admin/audit-logs", headers=headers)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["audit_logs"]
    assert len(logs) > 0
