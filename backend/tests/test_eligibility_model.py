"""
Unit and Integration Tests for the Machine Learning Eligibility Model Package.
Verifies model loading, exact documented predictions, validation constraints,
BMI calculations, role scoping, database persistence, and API contract invariants.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.eligibility_model_service import (
    eligibility_model_service,
    ApplicantEvaluationInput
)
from backend.app.db.sqlite_manager import sqlite_db


@pytest.fixture
def client():
    return TestClient(app)


# ==================== 1. MODEL SERVICE & CONTRACT TESTS ====================

def test_model_service_readiness_and_metadata():
    """Verify model loads successfully from authoritative package and returns metadata."""
    assert eligibility_model_service.is_ready() is True
    metadata = eligibility_model_service.get_metadata()
    assert metadata["model_name"] == "Gradient Boosting"
    assert metadata["feature_columns"] == ["age", "bmi", "smoker", "alcoholic", "pre_existing_condition"]
    assert "Diabetes" in metadata["allowed_values"]["pre_existing_condition"]


def test_documented_example_1_young_healthy():
    """Test documented Example 1: (28, 172, 68, 'No', 'No', 'None')."""
    inp = ApplicantEvaluationInput(
        age=28, height_cm=172, weight_kg=68,
        smoker="No", alcoholic="No", pre_existing_condition="None"
    )
    result = eligibility_model_service.evaluate(inp, user_role="customer")
    assert result.outcome == "ELIGIBLE"
    assert result.bmi == 22.99
    assert result.probability_eligible >= 0.95
    assert "HS-BASIC-001" in result.qualifying_plans
    assert "HS-GOLD-001" in result.qualifying_plans
    assert "EMP-INS-001" not in result.qualifying_plans


def test_documented_example_2_middle_aged_hypertension():
    """Test documented Example 2: (45, 165, 82, 'No', 'Yes', 'Hypertension')."""
    inp = ApplicantEvaluationInput(
        age=45, height_cm=165, weight_kg=82,
        smoker="No", alcoholic="Yes", pre_existing_condition="Hypertension"
    )
    result = eligibility_model_service.evaluate(inp, user_role="customer")
    assert result.outcome == "INELIGIBLE"
    assert result.bmi == 30.12
    assert result.probability_eligible < 0.20
    assert result.qualifying_plans == []


def test_documented_example_3_senior_heart_disease():
    """Test documented Example 3: (62, 170, 95, 'Yes', 'Yes', 'Heart_Disease')."""
    inp = ApplicantEvaluationInput(
        age=62, height_cm=170, weight_kg=95,
        smoker="Yes", alcoholic="Yes", pre_existing_condition="Heart_Disease"
    )
    result = eligibility_model_service.evaluate(inp, user_role="customer")
    assert result.outcome == "INELIGIBLE"
    assert result.bmi == 32.87
    assert result.probability_eligible == 0.0
    assert result.qualifying_plans == []


def test_readme_example():
    """Test README documented example: (35, 170, 70, 'No', 'No', 'None')."""
    inp = ApplicantEvaluationInput(
        age=35, height_cm=170, weight_kg=70,
        smoker="No", alcoholic="No", pre_existing_condition="None"
    )
    result = eligibility_model_service.evaluate(inp, user_role="customer")
    assert result.outcome == "ELIGIBLE"
    assert result.bmi == 24.22
    assert result.probability_eligible >= 0.95


def test_employee_role_receives_corporate_plan_when_eligible():
    """Verify corporate employee gets EMP-INS-001 when eligible."""
    inp = ApplicantEvaluationInput(
        age=30, height_cm=175, weight_kg=72,
        smoker="No", alcoholic="No", pre_existing_condition="None"
    )
    result = eligibility_model_service.evaluate(inp, user_role="employee")
    assert result.outcome == "ELIGIBLE"
    assert "EMP-INS-001" in result.qualifying_plans
    assert "HS-BASIC-001" in result.qualifying_plans


# ==================== 2. INPUT VALIDATION & CONSTRAINTS ====================

def test_validation_rejects_age_out_of_bounds():
    with pytest.raises(Exception):
        ApplicantEvaluationInput(
            age=17, height_cm=170, weight_kg=70,
            smoker="No", alcoholic="No", pre_existing_condition="None"
        )
    with pytest.raises(Exception):
        ApplicantEvaluationInput(
            age=101, height_cm=170, weight_kg=70,
            smoker="No", alcoholic="No", pre_existing_condition="None"
        )


def test_validation_rejects_height_weight_out_of_bounds():
    with pytest.raises(Exception):
        ApplicantEvaluationInput(
            age=30, height_cm=90, weight_kg=70,
            smoker="No", alcoholic="No", pre_existing_condition="None"
        )
    with pytest.raises(Exception):
        ApplicantEvaluationInput(
            age=30, height_cm=170, weight_kg=15,
            smoker="No", alcoholic="No", pre_existing_condition="None"
        )


def test_validation_rejects_invalid_condition_category():
    with pytest.raises(Exception):
        ApplicantEvaluationInput(
            age=30, height_cm=170, weight_kg=70,
            smoker="No", alcoholic="No", pre_existing_condition="UnknownAlienCondition"
        )


# ==================== 3. API ENDPOINT & WORKFLOW INTEGRATION ====================

def test_health_endpoint(client):
    res = client.get("/api/eligibility/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["model_loaded"] is True


def test_assess_requires_authentication(client):
    res = client.post("/api/eligibility/assess", json={
        "age": 30, "height_cm": 170, "weight_kg": 70,
        "smoker": "No", "alcoholic": "No", "pre_existing_condition": "None"
    })
    assert res.status_code == 401


def test_authenticated_assessment_and_plan_gating(client):
    # 1. Login as customer
    login_res = client.post("/api/auth/login", json={
        "email": "customer@insurance.com",
        "password": "Customer@123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit valid assessment
    assess_res = client.post("/api/eligibility/assess", headers=headers, json={
        "age": 28,
        "height_cm": 172,
        "weight_kg": 68,
        "smoker": "No",
        "alcoholic": "No",
        "pre_existing_condition": "None"
    })
    assert assess_res.status_code == 200
    assess_data = assess_res.json()
    assert assess_data["outcome"] == "ELIGIBLE"
    assert assess_data["bmi"] == 22.99
    assert assess_data["probability_eligible"] >= 0.95
    assessment_id = assess_data["assessment_id"]

    # 3. Retrieve current assessment via GET /me
    me_res = client.get("/api/eligibility/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["has_assessment"] is True
    assert me_data["assessment"]["assessment_id"] == assessment_id

    # 4. Select an authorized plan
    plan_res = client.post("/api/eligibility/select-plan", headers=headers, json={
        "selected_plan_id": "HS-GOLD-001"
    })
    assert plan_res.status_code == 200
    assert plan_res.json()["selected_plan_id"] == "HS-GOLD-001"

    # 5. Customer attempting to select employee-only plan is rejected
    invalid_plan_res = client.post("/api/eligibility/select-plan", headers=headers, json={
        "selected_plan_id": "EMP-INS-001"
    })
    assert invalid_plan_res.status_code == 403


def test_agent_contact_request_submission(client):
    login_res = client.post("/api/auth/login", json={
        "email": "customer@insurance.com",
        "password": "Customer@123"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    contact_res = client.post("/api/eligibility/agent-contact", headers=headers, json={
        "full_name": "Verified Customer",
        "email": "customer@insurance.com",
        "phone": "+1-555-0199",
        "preferred_contact_method": "PHONE",
        "notes": "Interested in specialized rider coverage"
    })
    assert contact_res.status_code == 200
    data = contact_res.json()
    assert data["status"] == "PENDING"
    assert "request_id" in data
