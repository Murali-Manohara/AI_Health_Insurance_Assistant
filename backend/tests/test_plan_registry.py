import pytest
from backend.app.registry.plans import (
    PLAN_REGISTRY,
    get_all_plans,
    get_plan_by_id,
    get_plan_by_filename
)

def test_four_canonical_plans_exist():
    assert len(PLAN_REGISTRY) == 4
    assert "HS-BASIC-001" in PLAN_REGISTRY
    assert "HS-GOLD-001" in PLAN_REGISTRY
    assert "HS-PREMIUM-001" in PLAN_REGISTRY
    assert "EMP-INS-001" in PLAN_REGISTRY

def test_plan_metadata_values():
    basic = get_plan_by_id("HS-BASIC-001")
    assert basic is not None
    assert basic.plan_name == "Health Shield – Basic"
    assert basic.plan_category == "Basic"
    assert basic.audience == "customer"
    assert basic.access_level == "customer"
    assert basic.expected_filename == "health_shield_basic.pdf"

    emp = get_plan_by_id("EMP-INS-001")
    assert emp is not None
    assert emp.plan_name == "Executive Employee Insurance Plan"
    assert emp.plan_category == "Employee Exclusive"
    assert emp.audience == "employee"
    assert emp.access_level == "employee"
    assert emp.data_status_default == "illustrative_unverified"

def test_lookup_by_filename():
    plan = get_plan_by_filename("health_shield_gold.pdf")
    assert plan is not None
    assert plan.plan_id == "HS-GOLD-001"

    missing = get_plan_by_filename("non_existent_plan.pdf")
    assert missing is None

def test_resolve_from_two_option_dropdown():
    from backend.app.registry.plans import resolve_plan_from_selection
    emp = resolve_plan_from_selection("Employee Insurance")
    assert emp is not None
    assert emp.plan_id == "EMP-INS-001"

    cust_gold = resolve_plan_from_selection("Customer Insurance", sample_text="HEALTH SHIELD - GOLD PLAN")
    assert cust_gold is not None
    assert cust_gold.plan_id == "HS-GOLD-001"
