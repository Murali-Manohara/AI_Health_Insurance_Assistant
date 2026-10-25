from fastapi import APIRouter, Depends
from backend.app.registry.plans import get_all_plans, get_plan_by_id
from backend.app.api.schemas.plans import PlanListResponse, PlanResponse
from backend.app.services.auth_service import UserIdentity, AuthorizationService
from backend.app.api.deps import get_auth_user

router = APIRouter(prefix="/plans", tags=["Plans"])

PLAN_DISPLAY_CONFIG = {
    "HS-BASIC-001": {
        "display_title": "Basic",
        "highlights": [
            "Entry-level fixed-benefit health protection",
            "Hospital Cash: \u20b92,000/day (up to 30 days/year)",
            "Day-Care Surgery & Major Surgery coverage up to \u20b950,000",
            "Initial 30-day waiting period; 2-year specific illness"
        ]
    },
    "HS-GOLD-001": {
        "display_title": "Gold",
        "highlights": [
            "Comprehensive customer healthcare coverage",
            "Hospital Cash: \u20b94,000/day | ICU: \u20b98,000/day",
            "Major Surgery benefit up to \u20b91,00,000 across Category 1-4",
            "Claim-free annual daily benefit increase of 5%"
        ]
    },
    "HS-PREMIUM-001": {
        "display_title": "Premium",
        "highlights": [
            "Highest-tier customer fixed-benefit coverage",
            "Hospital Cash: \u20b96,000/day | ICU: \u20b912,000/day",
            "Major Surgery benefit up to \u20b91,50,000 with recovery bonus",
            "Premium waiver on critical diagnosis & auto-health increase"
        ]
    },
    "EMP-INS-001": {
        "display_title": "Executive Employee",
        "highlights": [
            "Employee Exclusive group demonstration plan",
            "Corporate executive rider & comprehensive schedules",
            "Notice: Illustrative reference terms (not official product)",
            "Restricted to authenticated employee credentials"
        ]
    }
}

@router.get("", response_model=PlanListResponse)
def list_plans(user: UserIdentity = Depends(get_auth_user)):
    """
    Retrieve insurance plans accessible to the authenticated user.
    Customers receive Basic, Gold, and Premium.
    Employees receive all four canonical plans.
    """
    all_registered = get_all_plans()
    authorized_plans = AuthorizationService.get_authorized_plans(user.role)

    response_items = []
    for plan in all_registered:
        is_auth = plan.plan_id in authorized_plans
        # Show all plans, but customer cannot open unauthorized employee plan
        config = PLAN_DISPLAY_CONFIG.get(plan.plan_id, {
            "display_title": plan.plan_category,
            "highlights": []
        })

        # Only include employee plan in listing if role is employee or if explicitly listing
        if plan.plan_id == "EMP-INS-001" and user.role != "employee":
            continue

        response_items.append(PlanResponse(
            plan_id=plan.plan_id,
            plan_name=plan.plan_name,
            display_title=config["display_title"],
            plan_category=plan.plan_category,
            audience=plan.audience,
            access_level=plan.access_level,
            expected_filename=plan.expected_filename,
            data_status_default=plan.data_status_default,
            description=plan.description,
            highlights=config["highlights"],
            is_authorized=is_auth
        ))

    return PlanListResponse(
        plans=response_items,
        total=len(response_items),
        user_role=user.role
    )
