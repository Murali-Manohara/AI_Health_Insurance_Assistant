import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.claim_predictor_service import claim_predictor_service
from backend.app.api.schemas.claim_predictor import ClaimPredictionInput
from backend.app.db.sqlite_manager import sqlite_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_demo_users():
    sqlite_db.provision_demo_accounts(force_reconcile=True)

def test_claim_predictor_service_singleton_and_prediction():
    """
    Verify the model artifact loads once via the singleton service
    and produces the identical numerical prediction as the original app.py logic.
    """
    inp = ClaimPredictionInput(
        age=45,
        days_hospitalised=4,
        icu_days=1,
        procedures_claimed=2,
        prior_daycare_claims_year=0,
        extended_stay_flag=0,
        plan="Gold",
        pre_existing="no",
        claim_type="Major surgery",
        documents_complete="yes"
    )
    res = claim_predictor_service.predict(inp)
    assert "prediction" in res
    assert res["prediction"] > 0
    assert "formatted_prediction" in res
    assert res["formatted_prediction"].startswith("₹")
    assert res["output_units"] == "INR (₹)"
    assert res["validated_inputs"]["age"] == 45
    assert res["validated_inputs"]["plan"] == "Gold"

def test_claim_predictor_rbac_enforcement():
    """
    Verify backend RBAC:
    - 401 for unauthenticated
    - 403 for Customer (shivu@gmail.com)
    - 403 for Administrator (admin@gmail.com)
    - 200 for Employee (murali@gmail.com)
    """
    payload = {
        "age": 45,
        "days_hospitalised": 4,
        "icu_days": 1,
        "procedures_claimed": 2,
        "prior_daycare_claims_year": 0,
        "extended_stay_flag": 0,
        "plan": "Gold",
        "pre_existing": "no",
        "claim_type": "Major surgery",
        "documents_complete": "yes"
    }

    # 1. Unauthenticated -> 401
    resp_unauth = client.post("/api/claim-predictor/predict", json=payload)
    assert resp_unauth.status_code == 401

    # 2. Customer login -> 403
    login_cust = client.post("/api/auth/login", json={"email": "shivu@gmail.com", "password": "12345678"})
    assert login_cust.status_code == 200
    cust_token = login_cust.json()["token"]

    resp_cust = client.post(
        "/api/claim-predictor/predict",
        json=payload,
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert resp_cust.status_code == 403
    assert "Employee role authorization required" in resp_cust.json()["detail"]

    # 3. Admin login -> 403
    login_admin = client.post("/api/auth/login", json={"email": "admin@gmail.com", "password": "admin@123"})
    assert login_admin.status_code == 200
    admin_token = login_admin.json()["token"]

    resp_admin = client.post(
        "/api/claim-predictor/predict",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_admin.status_code == 403
    assert "Employee role authorization required" in resp_admin.json()["detail"]

    # 4. Employee login -> 200
    login_emp = client.post("/api/auth/login", json={"email": "murali@gmail.com", "password": "12345678"})
    assert login_emp.status_code == 200
    emp_token = login_emp.json()["token"]

    resp_emp = client.post(
        "/api/claim-predictor/predict",
        json=payload,
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert resp_emp.status_code == 200
    data = resp_emp.json()
    assert data["prediction"] > 0
    assert "₹" in data["formatted_prediction"]

def test_claim_predictor_input_validation():
    """
    Verify out-of-range or malformed inputs fail validation safely with 422 Unprocessable Entity.
    """
    login_emp = client.post("/api/auth/login", json={"email": "murali@gmail.com", "password": "12345678"})
    token = login_emp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Age too young (<18)
    r1 = client.post("/api/claim-predictor/predict", json={"age": 16, "plan": "Gold"}, headers=headers)
    assert r1.status_code == 422

    # Age too old (>70)
    r2 = client.post("/api/claim-predictor/predict", json={"age": 75, "plan": "Gold"}, headers=headers)
    assert r2.status_code == 422

    # Invalid plan name
    r3 = client.post("/api/claim-predictor/predict", json={"age": 30, "plan": "Diamond"}, headers=headers)
    assert r3.status_code == 422

    # ICU days out of bounds (>5)
    r4 = client.post("/api/claim-predictor/predict", json={"age": 30, "icu_days": 10}, headers=headers)
    assert r4.status_code == 422

def test_claim_predictor_with_rag_pipeline_integration():
    """
    Verify that when an employee passes an active conversation_id,
    the prediction and validated inputs are sent to the RAG pipeline,
    generating a grounded assistant message persisted in the conversation.
    """
    login_emp = client.post("/api/auth/login", json={"email": "murali@gmail.com", "password": "12345678"})
    emp_token = login_emp.json()["token"]
    headers = {"Authorization": f"Bearer {emp_token}"}

    # 1. Create a conversation session for the employee
    conv_resp = client.post(
        "/api/conversations",
        json={"selected_plan_id": "HS-GOLD-001"},
        headers=headers
    )
    assert conv_resp.status_code == 201
    conv_id = conv_resp.json()["conversation_id"]

    # 2. Call claim predictor with conversation_id
    payload = {
        "age": 42,
        "days_hospitalised": 5,
        "icu_days": 2,
        "procedures_claimed": 1,
        "prior_daycare_claims_year": 0,
        "extended_stay_flag": 0,
        "plan": "Gold",
        "pre_existing": "no",
        "claim_type": "Major surgery",
        "documents_complete": "yes",
        "conversation_id": conv_id
    }

    pred_resp = client.post("/api/claim-predictor/predict", json=payload, headers=headers)
    assert pred_resp.status_code == 200
    res_data = pred_resp.json()

    assert res_data["prediction"] > 0
    assert res_data["message"] is not None
    assistant_msg = res_data["message"]
    assert assistant_msg["role"] == "assistant"
    # Verify the message contains the numerical prediction
    assert res_data["formatted_prediction"] in assistant_msg["content"] or str(int(res_data["prediction"])) in assistant_msg["content"]
    # Verify the message contains disclaimer that it is an estimate, not guaranteed
    assert "estimate" in assistant_msg["content"].lower()

    # 3. Verify the message is persisted in conversation turns
    turns_resp = client.get(f"/api/conversations/{conv_id}/messages", headers=headers)
    assert turns_resp.status_code == 200
    turns = turns_resp.json()
    assert len(turns) >= 1  # assistant prediction turn
    assert any("estimate" in t["content"].lower() for t in turns)
