from pydantic import BaseModel
from typing import Optional

class PlanResponse(BaseModel):
    plan_id: str
    plan_name: str
    display_title: str
    plan_category: str
    audience: str
    access_level: str
    expected_filename: str
    data_status_default: str
    description: str
    highlights: list[str] = []
    is_authorized: bool = True

class PlanListResponse(BaseModel):
    plans: list[PlanResponse]
    total: int
    user_role: str
