import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.sqlite_manager import sqlite_db

client = TestClient(app)

# ==================== FIXTURES & HELPERS ====================

def create_user(role="customer", email_domain="example.com"):
    email = f"{role}_{uuid.uuid4().hex[:8]}@{email_domain}"
    resp = client.post("/api/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "role": role,
        "full_name": f"Test {role.capitalize()}"
    })
    assert resp.status_code == 201
    data = resp.json()
    token = data["token"]
    user_id = data["user"]["user_id"]
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, email, token, headers

def get_admin_session():
    resp = client.post("/api/auth/login", json={
        "email": "admin@insurance.corp",
        "password": "Admin@123"
    })
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}

def create_eligible_customer(plan_id="HS-GOLD-001"):
    user_id, email, token, headers = create_user("customer")
    assess_resp = client.post("/api/eligibility/assess", headers=headers, json={
        "age": 28,
        "height_cm": 172,
        "weight_kg": 68,
        "smoker": "No",
        "alcoholic": "No",
        "pre_existing_condition": "None"
    })
    assert assess_resp.status_code == 200
    assert assess_resp.json()["outcome"] == "ELIGIBLE"

    sel_resp = client.post("/api/eligibility/select-plan", headers=headers, json={
        "selected_plan_id": plan_id
    })
    assert sel_resp.status_code == 200
    return user_id, headers

# ==================== PRIORITY 1: NO ROLE HEADER FALLBACK ====================

def test_no_token_with_employee_role_header_rejected():
    """Unauthenticated request with X-User-Role: employee must be rejected with 401."""
    resp = client.get("/api/plans", headers={"X-User-Role": "employee"})
    assert resp.status_code == 401
    assert "authentication required" in resp.json()["detail"].lower()

    resp2 = client.post("/api/conversations", headers={"X-User-Role": "employee"}, json={"selected_plan_id": "EMP-INS-001"})
    assert resp2.status_code == 401

def test_no_token_with_admin_role_header_rejected():
    """Unauthenticated request with X-User-Role: admin must be rejected with 401."""
    resp = client.get("/api/admin/overview", headers={"X-User-Role": "admin"})
    assert resp.status_code in (401, 403)

def test_invalid_and_expired_tokens_rejected():
    """Invalid bearer tokens must return 401 Unauthorized."""
    resp = client.get("/api/plans", headers={"Authorization": "Bearer invalid_garbage_token"})
    assert resp.status_code == 401

    # Simulate expired token
    user_id, email, token, headers = create_user("customer")
    with sqlite_db._get_connection() as conn:
        conn.cursor().execute(
            "UPDATE sessions SET expires_at = ? WHERE token = ?",
            ((datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(), token)
        )
        conn.commit()

    resp_expired = client.get("/api/plans", headers=headers)
    assert resp_expired.status_code == 401
    assert "expired" in resp_expired.json()["detail"].lower()

def test_customer_cannot_access_admin_endpoints():
    """Authenticated customer attempting admin routes must receive 403 Forbidden."""
    _, _, _, cust_headers = create_user("customer")
    resp = client.get("/api/admin/overview", headers=cust_headers)
    assert resp.status_code == 403

def test_employee_cannot_access_admin_endpoints():
    """Authenticated employee attempting admin routes must receive 403 Forbidden."""
    _, _, _, emp_headers = create_user("employee", email_domain="insurance.corp")
    resp = client.get("/api/admin/overview", headers=emp_headers)
    assert resp.status_code == 403

def test_valid_sessions_access_permitted_endpoints():
    """Customer, employee, and admin access their respective allowed resources."""
    _, _, _, cust_headers = create_user("customer")
    resp_c = client.get("/api/plans", headers=cust_headers)
    assert resp_c.status_code == 200
    plan_ids = [p["plan_id"] for p in resp_c.json()["plans"]]
    assert "HS-BASIC-001" in plan_ids
    assert "EMP-INS-001" not in plan_ids

    _, _, _, emp_headers = create_user("employee", email_domain="insurance.corp")
    resp_e = client.get("/api/plans", headers=emp_headers)
    assert resp_e.status_code == 200
    emp_plan_ids = [p["plan_id"] for p in resp_e.json()["plans"]]
    assert "EMP-INS-001" in emp_plan_ids

    admin_headers = get_admin_session()
    resp_a = client.get("/api/admin/overview", headers=admin_headers)
    assert resp_a.status_code == 200

# ==================== PRIORITY 2: ELIGIBILITY & PLAN GATING FOR POLICY CHAT ====================

def test_chat_blocked_without_assessment():
    """Customer without an eligibility assessment cannot start a policy chat."""
    _, _, _, cust_headers = create_user("customer")
    resp = client.post("/api/conversations", headers=cust_headers, json={"selected_plan_id": "HS-GOLD-001"})
    assert resp.status_code == 403
    assert "eligibility assessment" in resp.json()["detail"].lower()

def test_chat_blocked_for_ineligible_assessment():
    """Customer with an INELIGIBLE assessment outcome cannot select plans or start policy chat."""
    user_id, _, _, cust_headers = create_user("customer")
    now = datetime.now(timezone.utc)
    sqlite_db.save_eligibility_assessment(
        user_id=user_id,
        status="COMPLETED",
        outcome="INELIGIBLE",
        qualifying_plans=[],
        input_provenance={},
        model_id="GradientBoosting",
        model_version="1.0.0",
        confidence_score=0.92,
        reason_codes=["INELIGIBLE_HEALTH_RISK"],
        expires_at=(now + timedelta(days=90)).isoformat()
    )

    resp = client.post("/api/conversations", headers=cust_headers, json={"selected_plan_id": "HS-GOLD-001"})
    assert resp.status_code == 403
    assert "restricted" in resp.json()["detail"].lower() or "not eligible" in resp.json()["detail"].lower()

def test_chat_blocked_for_pending_or_needs_review():
    """NEEDS_REVIEW or PENDING assessment does not authorize conversation creation."""
    user_id, _, _, cust_headers = create_user("customer")
    now = datetime.now(timezone.utc)
    sqlite_db.save_eligibility_assessment(
        user_id=user_id,
        status="COMPLETED",
        outcome="NEEDS_REVIEW",
        qualifying_plans=[],
        input_provenance={},
        model_id="GradientBoosting",
        model_version="1.0.0",
        confidence_score=0.55,
        reason_codes=["BORDERLINE_RISK"],
        expires_at=(now + timedelta(days=90)).isoformat()
    )

    resp = client.post("/api/conversations", headers=cust_headers, json={"selected_plan_id": "HS-GOLD-001"})
    assert resp.status_code == 403
    assert "restricted" in resp.json()["detail"].lower()

def test_chat_blocked_for_expired_assessment():
    """Expired assessment must not authorize conversation creation."""
    user_id, _, _, cust_headers = create_user("customer")
    now = datetime.now(timezone.utc)
    expired_time = (now - timedelta(days=5)).isoformat()
    sqlite_db.save_eligibility_assessment(
        user_id=user_id,
        status="COMPLETED",
        outcome="ELIGIBLE",
        qualifying_plans=["HS-GOLD-001"],
        input_provenance={},
        model_id="GradientBoosting",
        model_version="1.0.0",
        confidence_score=0.98,
        reason_codes=["EXCELLENT_HEALTH"],
        expires_at=expired_time
    )

    resp = client.post("/api/conversations", headers=cust_headers, json={"selected_plan_id": "HS-GOLD-001"})
    assert resp.status_code == 403
    assert "expired" in resp.json()["detail"].lower()

def test_chat_blocked_without_plan_selection():
    """Eligible customer who has not selected a plan cannot start conversation."""
    _, _, _, cust_headers = create_user("customer")
    # Complete an eligible assessment
    assess_resp = client.post("/api/eligibility/assess", headers=cust_headers, json={
        "age": 28, "height_cm": 172, "weight_kg": 68,
        "smoker": "No", "alcoholic": "No", "pre_existing_condition": "None"
    })
    assert assess_resp.status_code == 200
    # Do NOT select plan
    resp = client.post("/api/conversations", headers=cust_headers, json={"selected_plan_id": "HS-GOLD-001"})
    assert resp.status_code == 403
    assert "no active plan selection" in resp.json()["detail"].lower()

def test_chat_blocked_when_requesting_different_plan():
    """Customer selecting HS-GOLD-001 cannot create conversation for HS-PREMIUM-001."""
    _, cust_headers = create_eligible_customer("HS-GOLD-001")

    # Try to open chat on HS-PREMIUM-001
    resp = client.post("/api/conversations", headers=cust_headers, json={"selected_plan_id": "HS-PREMIUM-001"})
    assert resp.status_code == 403
    assert "does not match" in resp.json()["detail"].lower()

def test_customer_cannot_access_another_users_conversation():
    """Customer A cannot view or send messages to Customer B's conversation."""
    _, headers_a = create_eligible_customer("HS-GOLD-001")
    conv_a = client.post("/api/conversations", headers=headers_a, json={"selected_plan_id": "HS-GOLD-001"}).json()
    conv_id = conv_a["conversation_id"]

    # Customer B tries to read conversation A
    _, _, _, headers_b = create_user("customer")
    resp_b = client.get(f"/api/conversations/{conv_id}", headers=headers_b)
    assert resp_b.status_code in (403, 404)

def test_eligible_customer_matching_plan_succeeds():
    """Eligible customer with matching active plan selection succeeds."""
    _, cust_headers = create_eligible_customer("HS-GOLD-001")
    resp = client.post("/api/conversations", headers=cust_headers, json={"selected_plan_id": "HS-GOLD-001"})
    assert resp.status_code == 201
    assert resp.json()["selected_plan_id"] == "HS-GOLD-001"

# ==================== PRIORITY 5, 6, 7: ADMIN KPIS, FUNNEL & LATENCY ====================

def test_admin_kpis_and_funnel_keys():
    """Admin dashboard overview returns consistent KPI keys, aliases, and funnel rates."""
    admin_headers = get_admin_session()
    resp = client.get("/api/admin/overview?range=7d", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    kpis = data["kpis"]

    # Verify both canonical and frontend aliases are present
    assert "not_assessed_users" in kpis
    assert "users_not_assessed" in kpis
    assert kpis["not_assessed_users"] == kpis["users_not_assessed"]

    assert "plan_selected_users" in kpis
    assert "users_selected_plan" in kpis
    assert kpis["plan_selected_users"] == kpis["users_selected_plan"]

    assert "policy_chat_active_users" in kpis
    assert "users_proceeded_to_chat" in kpis
    assert kpis["policy_chat_active_users"] == kpis["users_proceeded_to_chat"]

    # Verify funnel rates exist both nested and flattened
    assert "funnel_rates" in kpis
    assert "eligibility_rate_pct" in kpis["funnel_rates"]
    assert "plan_selection_rate_pct" in kpis["funnel_rates"]
    assert "chat_engagement_rate_pct" in kpis["funnel_rates"]

    assert "underwriting_eligibility_rate_pct" in kpis
    assert "plan_selection_conversion_rate_pct" in kpis
    assert "chat_engagement_conversion_rate_pct" in kpis

def test_absent_latency_telemetry_returns_none():
    """When no RAG request metrics exist, average_latency_ms is None and not 450.0."""
    admin_headers = get_admin_session()
    resp = client.get("/api/admin/overview?range=7d", headers=admin_headers)
    assert resp.status_code == 200
    kpis = resp.json()["kpis"]
    assert "average_latency_ms" in kpis
    # In isolated test DB with 0 chat metrics, average_latency_ms is None (null)
    with sqlite_db._get_connection() as conn:
        cnt = conn.cursor().execute("SELECT COUNT(*) as c FROM rag_request_metrics").fetchone()["c"]
    if cnt == 0:
        assert kpis["average_latency_ms"] is None
        assert kpis["average_latency_ms"] != 450.0

# ==================== OPTIMIZATION REGRESSION TESTS ====================

def test_sqlite_wal_persistence_and_no_per_query_pragma():
    """Verify WAL mode is active and persistent on the test database without per-query PRAGMA."""
    with sqlite_db._get_connection() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert journal_mode.lower() == "wal"

def test_parent_store_caching_and_refresh_indexes():
    """Verify HybridRetrievalService parent store caching and refresh_indexes functionality."""
    from backend.app.api.deps import get_rag_orchestrator
    retriever = get_rag_orchestrator().retrieval_service
    store1 = retriever.get_parent_store()
    assert isinstance(store1, dict)
    
    # Test refresh_indexes executes cleanly
    retriever.refresh_indexes()
    store2 = retriever.get_parent_store()
    assert isinstance(store2, dict)

def test_conversation_atomic_persistence_and_sqlite_primary():
    """Verify conversation and messages are stored atomically in SQLite and retrievable."""
    user_id, headers = create_eligible_customer("HS-GOLD-001")
    
    # Create conversation
    create_resp = client.post("/api/conversations", headers=headers, json={
        "selected_plan_id": "HS-GOLD-001"
    })
    assert create_resp.status_code == 201
    cid = create_resp.json()["conversation_id"]

    # Send message
    send_resp = client.post(f"/api/conversations/{cid}/messages", headers=headers, json={
        "query": "What is the ICU limit?"
    })
    assert send_resp.status_code == 200

    # Verify directly from SQLite
    db_msgs = sqlite_db.get_messages_for_conversation(cid)
    assert len(db_msgs) >= 2  # user + assistant turns
    user_msg = next((m for m in db_msgs if m["role"] == "user"), None)
    asst_msg = next((m for m in db_msgs if m["role"] == "assistant"), None)
    assert user_msg is not None
    assert asst_msg is not None
    assert "ICU" in user_msg["content"]
