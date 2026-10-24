import re
from typing import Optional
from pydantic import BaseModel, Field
from backend.app.services.auth_service import AuthorizationService, EMPLOYEE_ONLY_PLANS
from backend.app.registry.plans import get_plan_by_id
from backend.app.core.logging_config import logger

class ScopeResolutionResult(BaseModel):
    selected_plan_id: str
    authorized_plans: list[str]
    effective_scope: list[str]
    reason: str  # "greeting", "default_selected_plan", "explicit_comparison", "follow_up", "clarification_needed", "access_restricted"
    is_comparison: bool = False
    is_ambiguous: bool = False
    is_greeting: bool = False
    greeting_message: Optional[str] = None
    clarification_prompt: Optional[str] = None
    resolved_query: Optional[str] = None
    denied_plans: list[str] = Field(default_factory=list)

PLAN_KEYWORDS: dict[str, str] = {
    "basic": "HS-BASIC-001",
    "hs-basic": "HS-BASIC-001",
    "hs-basic-001": "HS-BASIC-001",
    "gold": "HS-GOLD-001",
    "hs-gold": "HS-GOLD-001",
    "hs-gold-001": "HS-GOLD-001",
    "premium": "HS-PREMIUM-001",
    "hs-premium": "HS-PREMIUM-001",
    "hs-premium-001": "HS-PREMIUM-001",
    "employee": "EMP-INS-001",
    "executive": "EMP-INS-001",
    "emp-ins": "EMP-INS-001",
    "emp-ins-001": "EMP-INS-001"
}

GREETING_PATTERN = re.compile(
    r"^(?:hello|hi|hey|greetings|howdy|good\s+(?:morning|afternoon|evening)|hi\s+there|hello\s+there)[!.,\s]*$",
    re.IGNORECASE
)

class ScopeResolver:
    """
    Determines effective retrieval scope for a query in a plan-scoped session.
    Enforces authorization, preserves conversation plan scope by default,
    and safely expands scope only for explicit authorized comparisons.
    """

    @staticmethod
    def resolve_scope(
        query: str,
        selected_plan_id: str,
        role: str,
        conversation_history: Optional[list[dict]] = None
    ) -> ScopeResolutionResult:
        q_lower = query.lower().strip()
        authorized_set = AuthorizationService.get_authorized_plans(role)
        authorized_list = sorted(list(authorized_set))

        # Ensure selected plan is authorized
        if selected_plan_id not in authorized_set:
            selected_plan_id = "HS-BASIC-001" if "HS-BASIC-001" in authorized_set else authorized_list[0]

        # 0. Check for Greeting query
        if GREETING_PATTERN.match(q_lower):
            p_info = get_plan_by_id(selected_plan_id)
            p_name = p_info.plan_name if p_info else selected_plan_id
            greeting_msg = f"Hello! I can help you understand the benefits, limits, waiting periods, and claim conditions described in {p_name}. What would you like to know?"
            return ScopeResolutionResult(
                selected_plan_id=selected_plan_id,
                authorized_plans=authorized_list,
                effective_scope=[selected_plan_id],
                reason="greeting",
                is_comparison=False,
                is_ambiguous=False,
                is_greeting=True,
                greeting_message=greeting_msg
            )

        general_compare_patterns = [
            r"^(?:compare|difference\s+between|which\s+is\s+better)\s+(?:the\s+)?plans\??$",
            r"^(?:which\s+plan\s+is\s+better|which\s+one\s+is\s+better)\??$",
            r"^(?:compare\s+all|compare\s+them|how\s+do\s+they\s+compare)\??$"
        ]
        if any(re.search(pat, q_lower) for pat in general_compare_patterns):
            logger.info("Ambiguous comparison detected. Requesting clarification.")
            return ScopeResolutionResult(
                selected_plan_id=selected_plan_id,
                authorized_plans=authorized_list,
                effective_scope=[selected_plan_id],
                reason="clarification_needed",
                is_comparison=True,
                is_ambiguous=True,
                clarification_prompt="Which plans would you like to compare? You can compare Basic, Gold, and Premium (or ask to compare all customer plans)."
            )

        # 2. Check for "compare all three" / "compare customer plans"
        all_customer_patterns = [
            r"compare\s+all\s+(?:three|3)",
            r"all\s+(?:three|3)\s+(?:customer\s+)?plans",
            r"compare\s+(?:all\s+)?customer\s+plans"
        ]
        if any(re.search(pat, q_lower) for pat in all_customer_patterns):
            customer_plans = ["HS-BASIC-001", "HS-GOLD-001", "HS-PREMIUM-001"]
            effective = [p for p in customer_plans if p in authorized_set]
            return ScopeResolutionResult(
                selected_plan_id=selected_plan_id,
                authorized_plans=authorized_list,
                effective_scope=effective,
                reason="explicit_comparison",
                is_comparison=True,
                is_ambiguous=False
            )

        # 3. Detect explicitly mentioned plans in query
        detected_plans = set()
        
        # Explicit comparison trigger terms
        comparison_triggers = ["compare", "versus", "vs", "difference between", "better than", "instead of", "as opposed to"]
        has_comparison_trigger = any(t in q_lower for t in comparison_triggers)

        # Word boundary search for plan names
        for word, pid in PLAN_KEYWORDS.items():
            pattern = rf"\b{re.escape(word)}\b"
            if re.search(pattern, q_lower):
                detected_plans.add(pid)

        # Check for unauthorized employee plan request by a customer
        denied_plans = []
        for pid in list(detected_plans):
            if pid not in authorized_set:
                detected_plans.remove(pid)
                denied_plans.append(pid)
                logger.warning(f"Role '{role}' attempted to request unauthorized plan '{pid}' in query.")

        # If a comparison trigger exists and at least one other plan is mentioned:
        if has_comparison_trigger and detected_plans:
            # Include the current selected plan if only 1 other plan was named (e.g. "compare with Gold")
            combined_scope = set(detected_plans)
            if len(combined_scope) == 1 and selected_plan_id in authorized_set:
                combined_scope.add(selected_plan_id)

            effective = [p for p in authorized_list if p in combined_scope]
            if len(effective) > 1:
                reason = "explicit_comparison"
                if denied_plans:
                    reason = "access_restricted"
                return ScopeResolutionResult(
                    selected_plan_id=selected_plan_id,
                    authorized_plans=authorized_list,
                    effective_scope=effective,
                    reason=reason,
                    is_comparison=True,
                    is_ambiguous=False,
                    denied_plans=denied_plans
                )

        # If user explicitly asked ONLY for a different plan without a comparison trigger
        # e.g. "What does Gold cover?" while currently in Basic conversation:
        if detected_plans and len(detected_plans) == 1 and not has_comparison_trigger:
            only_plan = list(detected_plans)[0]
            if only_plan != selected_plan_id:
                return ScopeResolutionResult(
                    selected_plan_id=selected_plan_id,
                    authorized_plans=authorized_list,
                    effective_scope=[only_plan],
                    reason="explicit_named_plan",
                    is_comparison=False,
                    is_ambiguous=False,
                    denied_plans=denied_plans
                )

        # If customer asked solely for an employee plan
        if denied_plans and not detected_plans:
            return ScopeResolutionResult(
                selected_plan_id=selected_plan_id,
                authorized_plans=authorized_list,
                effective_scope=[selected_plan_id],
                reason="access_restricted",
                is_comparison=False,
                is_ambiguous=False,
                denied_plans=denied_plans
            )

        # 4. Follow-up / Default Selected Plan Scope
        # Pronouns ("it", "this plan", "its", "the policy") or general questions
        reason = "default_selected_plan"
        resolved_q = query
        follow_up_tokens = ["its", "it", "that", "those", "this", "these", "does it", "is there", "what is", "what about"]
        if any(re.search(rf"\b{t}\b", q_lower) for t in follow_up_tokens):
            reason = "follow_up"
            if conversation_history:
                last_turn = conversation_history[-1]
                last_q = last_turn.get("user_query") or last_turn.get("query") or ""
                # If current query contains core pronouns, enrich retrieval query with last question's topic
                if last_q and any(p in q_lower.split() for p in ["its", "it", "that", "those", "this", "there", "what", "how"]):
                    resolved_q = f"{last_q} — {query}"

        return ScopeResolutionResult(
            selected_plan_id=selected_plan_id,
            authorized_plans=authorized_list,
            effective_scope=[selected_plan_id],
            reason=reason,
            is_comparison=False,
            is_ambiguous=False,
            resolved_query=resolved_q,
            denied_plans=denied_plans
        )
