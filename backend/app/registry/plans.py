from typing import Optional
from pydantic import BaseModel

class PlanInfo(BaseModel):
    plan_id: str
    plan_name: str
    plan_category: str
    audience: str
    access_level: str
    expected_filename: str
    data_status_default: str
    description: str

PLAN_REGISTRY: dict[str, PlanInfo] = {
    "HS-BASIC-001": PlanInfo(
        plan_id="HS-BASIC-001",
        plan_name="Health Shield – Basic",
        plan_category="Basic",
        audience="customer",
        access_level="customer",
        expected_filename="health_shield_basic.pdf",
        data_status_default="verified",
        description="Entry-level fixed-benefit health insurance plan for customers."
    ),
    "HS-GOLD-001": PlanInfo(
        plan_id="HS-GOLD-001",
        plan_name="Health Shield – Gold",
        plan_category="Gold",
        audience="customer",
        access_level="customer",
        expected_filename="health_shield_gold.pdf",
        data_status_default="verified",
        description="Comprehensive fixed-benefit health insurance plan for customers."
    ),
    "HS-PREMIUM-001": PlanInfo(
        plan_id="HS-PREMIUM-001",
        plan_name="Health Shield – Premium",
        plan_category="Premium",
        audience="customer",
        access_level="customer",
        expected_filename="health_shield_premium.pdf",
        data_status_default="verified",
        description="Premium high-tier fixed-benefit health insurance plan for customers."
    ),
    "EMP-INS-001": PlanInfo(
        plan_id="EMP-INS-001",
        plan_name="Executive Employee Insurance Plan",
        plan_category="Employee Exclusive",
        audience="employee",
        access_level="employee",
        expected_filename="executive_employee_insurance_plan.pdf",
        data_status_default="illustrative_unverified",
        description="Executive employee group insurance with illustrative and unverified policy schedules."
    ),
}

def get_all_plans() -> list[PlanInfo]:
    """Return all registered plans."""
    return list(PLAN_REGISTRY.values())

def get_plan_by_id(plan_id: str) -> Optional[PlanInfo]:
    """Retrieve plan by its canonical ID."""
    return PLAN_REGISTRY.get(plan_id)

def get_plan_by_filename(filename: str) -> Optional[PlanInfo]:
    """Find registered plan matching expected filename."""
    clean_name = filename.lower()
    for plan in PLAN_REGISTRY.values():
        if plan.expected_filename.lower() == clean_name:
            return plan
    return None

def resolve_plan_from_selection(selection: str, sample_text: str = "") -> Optional[PlanInfo]:
    """
    Resolves plan from either exact plan_id or from the 2-option selection:
    'customer' (Customer Insurance) vs 'employee' (Employee Insurance).
    If 'customer', inspects sample_text to auto-determine Basic, Gold, or Premium.
    """
    sel_lower = selection.strip().lower()
    
    # 1. Direct ID match
    if selection in PLAN_REGISTRY:
        return PLAN_REGISTRY[selection]

    # 2. Employee Insurance selection
    if "employee" in sel_lower or "emp" in sel_lower:
        return PLAN_REGISTRY["EMP-INS-001"]

    # 3. Customer Insurance selection: detect specific tier from PDF header text
    if "customer" in sel_lower or "health" in sel_lower or "shield" in sel_lower:
        text_lower = sample_text.lower()
        if any(k in text_lower for k in ["hs-gold-001", "gold plan", "shield – gold", "shield - gold", "category: gold", "shield gold"]):
            return PLAN_REGISTRY["HS-GOLD-001"]
        elif any(k in text_lower for k in ["hs-premium-001", "premium plan", "shield – premium", "shield - premium", "category: premium", "shield premium"]):
            return PLAN_REGISTRY["HS-PREMIUM-001"]
        elif any(k in text_lower for k in ["hs-basic-001", "basic plan", "shield – basic", "shield - basic", "category: basic", "shield basic"]):
            return PLAN_REGISTRY["HS-BASIC-001"]
        # Default customer fallback if undetermined
        return PLAN_REGISTRY["HS-BASIC-001"]

    return None
