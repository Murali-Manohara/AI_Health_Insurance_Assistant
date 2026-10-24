import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.scope_resolver import ScopeResolver
from backend.app.services.bm25_service import BM25SearchService
from backend.app.services.retrieval_service import HybridRetrievalService

client = TestClient(app)

def test_scope_resolver_default_and_followup():
    """Selected plan is default; pronouns retain selected plan."""
    res1 = ScopeResolver.resolve_scope("What is hospital cash?", "HS-BASIC-001", "customer")
    assert res1.effective_scope == ["HS-BASIC-001"]
    assert res1.is_comparison is False

    res2 = ScopeResolver.resolve_scope("What is its waiting period?", "HS-GOLD-001", "customer")
    assert res2.effective_scope == ["HS-GOLD-001"]
    assert res2.reason == "follow_up"

def test_scope_resolver_explicit_comparison():
    """Explicitly comparing two plans expands scope to both authorized plans."""
    res = ScopeResolver.resolve_scope("Compare Basic and Gold surgery limits", "HS-BASIC-001", "customer")
    assert res.is_comparison is True
    assert set(res.effective_scope) == {"HS-BASIC-001", "HS-GOLD-001"}

def test_scope_resolver_ambiguous_comparison():
    """Ambiguous query like 'compare plans' flags clarification needed."""
    res = ScopeResolver.resolve_scope("compare plans", "HS-BASIC-001", "customer")
    assert res.is_ambiguous is True
    assert res.reason == "clarification_needed"
    assert "Which plans would you like to compare" in (res.clarification_prompt or "")

def test_silver_never_silently_mapped_to_premium():
    """Unknown or unverified 'Silver' plan ID fails validation and is rejected."""
    resp = client.post(
        "/api/conversations",
        json={"selected_plan_id": "HS-SILVER-001"}
    )
    assert resp.status_code == 403

def test_bm25_exact_keyword_matching():
    """BM25 search returns relevant exact-term matches with valid scores."""
    bm25 = BM25SearchService()
    results = bm25.search("waiting period 30 days", ["HS-BASIC-001", "HS-GOLD-001"], top_k=3)
    assert len(results) > 0
    assert results[0]["score"] > 0
    assert "waiting" in results[0]["content"].lower()

def test_hybrid_rrf_and_citation_provenance():
    """Hybrid retrieval returns deduplicated chunks with valid metadata and provenance."""
    retrieval_svc = HybridRetrievalService()
    res = retrieval_svc.retrieve(
        query="Major Surgery benefit",
        role="customer",
        effective_scope=["HS-GOLD-001"],
        top_k=3
    )
    assert len(res["chunks"]) > 0
    for chunk in res["chunks"]:
        assert chunk["plan_id"] == "HS-GOLD-001"
        assert "metadata" in chunk
        assert "source_page_start" in chunk["metadata"]
        assert "source_page_end" in chunk["metadata"]

def test_employee_plan_illustrative_warning():
    """Employee conversation preserves illustrative_unverified notice."""
    c_resp = client.post(
        "/api/conversations",
        headers={"X-User-Role": "employee"},
        json={"selected_plan_id": "EMP-INS-001"}
    )
    assert c_resp.status_code == 201
    conv_id = c_resp.json()["conversation_id"]

    m_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers={"X-User-Role": "employee"},
        json={"query": "What are the surgery benefits?"}
    )
    assert m_resp.status_code == 200
    msg_data = m_resp.json()["message"]
    assert msg_data["contains_unverified_notice"] is True
    assert "illustrative" in msg_data["content"].lower()

def test_list_conversations_endpoint_and_rbac():
    """Verify that empty conversations are excluded, and customer cannot see employee history."""
    # 1. Create a customer conversation
    c_resp = client.post(
        "/api/conversations",
        headers={"X-User-Role": "customer"},
        json={"selected_plan_id": "HS-GOLD-001"}
    )
    assert c_resp.status_code == 201
    conv_id = c_resp.json()["conversation_id"]

    # Before any message, empty chat is NOT stored in history
    list_resp = client.get("/api/conversations", headers={"X-User-Role": "customer"})
    assert list_resp.status_code == 200
    assert not any(item["conversation_id"] == conv_id for item in list_resp.json())

    # Send a query
    m_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers={"X-User-Role": "customer"},
        json={"query": "What is the hospital cash benefit?"}
    )
    assert m_resp.status_code == 200

    # Now it must be stored and returned in history
    list_resp2 = client.get("/api/conversations", headers={"X-User-Role": "customer"})
    assert list_resp2.status_code == 200
    items = list_resp2.json()
    assert any(item["conversation_id"] == conv_id for item in items)

    # 2. RBAC check: Employee conversation with EMP-INS-001
    emp_c_resp = client.post(
        "/api/conversations",
        headers={"X-User-Role": "employee"},
        json={"selected_plan_id": "EMP-INS-001"}
    )
    assert emp_c_resp.status_code == 201
    emp_conv_id = emp_c_resp.json()["conversation_id"]
    client.post(
        f"/api/conversations/{emp_conv_id}/messages",
        headers={"X-User-Role": "employee"},
        json={"query": "Staff surgery benefits"}
    )

    # Customer MUST NOT see employee conversation in history
    cust_history = client.get("/api/conversations", headers={"X-User-Role": "customer"}).json()
    assert not any(item.get("selected_plan_id") == "EMP-INS-001" for item in cust_history)

    # Customer MUST NOT be allowed to access employee conversation directly (Fails closed 404/403)
    forbidden_resp = client.get(f"/api/conversations/{emp_conv_id}", headers={"X-User-Role": "customer"})
    assert forbidden_resp.status_code == 404


