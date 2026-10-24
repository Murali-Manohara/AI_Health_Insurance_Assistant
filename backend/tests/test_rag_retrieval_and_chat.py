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
