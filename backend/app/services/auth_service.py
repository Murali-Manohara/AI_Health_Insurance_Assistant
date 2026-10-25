import re
from typing import Optional, Set
from pydantic import BaseModel
from fastapi import Request, HTTPException, status
import bcrypt
from backend.app.db.sqlite_manager import sqlite_db
from backend.app.core.logging_config import logger

class UserIdentity(BaseModel):
    user_id: str
    role: str  # "customer" or "employee"
    full_name: str = "User"
    email: Optional[str] = None

# Canonical plans authorized per role
ROLE_PLAN_PERMISSIONS: dict[str, Set[str]] = {
    "customer": {"HS-BASIC-001", "HS-GOLD-001", "HS-PREMIUM-001"},
    "employee": {"HS-BASIC-001", "HS-GOLD-001", "HS-PREMIUM-001", "EMP-INS-001"},
    "admin": {"HS-BASIC-001", "HS-GOLD-001", "HS-PREMIUM-001", "EMP-INS-001"}
}

EMPLOYEE_ONLY_PLANS: Set[str] = {"EMP-INS-001"}

# Pre-authorized corporate domain patterns for employee verification
AUTHORIZED_EMPLOYEE_DOMAINS = ("@insurance.corp", "@corporate.internal")

def hash_password(plain_password: str) -> str:
    """Hash plaintext password using bcrypt with salt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error(f"Error checking password: {e}")
        return False

def register_user(
    email: str,
    password: str,
    requested_role: str = "customer",
    full_name: Optional[str] = None
) -> tuple[dict, str, Optional[str]]:
    """
    Registers a new user, hashes password, enforces employee protection,
    creates an active SQLite session, and returns (user_dict, token, message).
    """
    clean_email = email.strip().lower()
    existing = sqlite_db.get_user_by_email(clean_email)
    if existing:
        logger.warning(f"Registration rejected: duplicate email '{clean_email}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please log in."
        )

    # Server-enforced role protection:
    # 1. Administrator accounts cannot be created through public registration
    req_role = requested_role.strip().lower()
    if req_role == "admin":
        logger.warning(f"Registration attempt with restricted 'admin' role rejected for email '{clean_email}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator accounts cannot be created via public registration. Contact system governance."
        )

    # 2. Self-selecting Employee does not grant employee access unless corporate domain is verified.
    effective_role = "customer"
    is_approved = 1
    notice_message = None

    if req_role == "employee":
        if any(clean_email.endswith(d) for d in AUTHORIZED_EMPLOYEE_DOMAINS):
            effective_role = "employee"
            is_approved = 1
            notice_message = "Corporate employee identity verified."
        else:
            # Keep newly registered employee accounts unprivileged / pending approval
            effective_role = "customer"
            is_approved = 0
            notice_message = (
                "Employee role registration submitted. For security governance, "
                "standard customer access is granted pending administrative verification."
            )
            logger.info(f"User {clean_email} requested employee role; assigned customer access pending approval.")
    else:
        effective_role = "customer"
        is_approved = 1

    pw_hash = hash_password(password)
    display_name = full_name.strip() if full_name and full_name.strip() else ("Employee Staff" if effective_role == "employee" else "Customer Member")

    user_record = sqlite_db.create_user(
        email=clean_email,
        password_hash=pw_hash,
        requested_role=req_role,
        effective_role=effective_role,
        is_approved=is_approved,
        full_name=display_name
    )

    token = sqlite_db.create_session(user_record["user_id"], user_record["role"])
    logger.info(f"User registered successfully: id={user_record['user_id']} role={user_record['role']}")
    return user_record, token, notice_message

def authenticate_user(email: str, password: str) -> tuple[dict, str]:
    """
    Authenticates user credentials against SQLite database.
    Returns (user_dict, token) on success or raises 401.
    """
    clean_email = email.strip().lower()
    user = sqlite_db.get_user_by_email(clean_email)
    if not user:
        logger.warning(f"Authentication failed: user not found '{clean_email}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not verify_password(password, user["password_hash"]):
        logger.warning(f"Authentication failed: invalid password for '{clean_email}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    token = sqlite_db.create_session(user["user_id"], user["effective_role"])
    logger.info(f"User authenticated successfully: id={user['user_id']} role={user['effective_role']}")
    return user, token

def logout_session(token: str) -> bool:
    """Invalidates active session token."""
    return sqlite_db.delete_session(token)

class AuthorizationService:
    """
    Centralized server-side authorization service enforcing strict
    role-based access control (RBAC) across plans, search scopes, and citations.
    """

    @staticmethod
    def get_authorized_plans(role: str) -> Set[str]:
        """Return the immutable set of canonical plan IDs authorized for a role."""
        return ROLE_PLAN_PERMISSIONS.get(role.lower().strip(), set())

    @staticmethod
    def is_plan_authorized(role: str, plan_id: str) -> bool:
        """Check if a specific canonical plan ID is accessible by the role."""
        authorized = AuthorizationService.get_authorized_plans(role)
        return plan_id in authorized

    @staticmethod
    def filter_authorized_plans(role: str, requested_plans: list[str]) -> list[str]:
        """
        Intersect requested plans with the role's authorized plans.
        Never grants access to unauthorized plans even if requested by client.
        """
        authorized = AuthorizationService.get_authorized_plans(role)
        return [p for p in requested_plans if p in authorized]

    @staticmethod
    def validate_plan_access(role: str, plan_id: str) -> None:
        """Raise 403 Forbidden if the user role is not authorized for the plan."""
        if not AuthorizationService.is_plan_authorized(role, plan_id):
            logger.warning(f"Unauthorized access attempt: role='{role}' attempted to access plan='{plan_id}'")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Your account role ({role}) does not have permission to access plan '{plan_id}'."
            )

    @staticmethod
    def sanitize_retrieved_chunks(role: str, chunks: list[dict]) -> list[dict]:
        """
        Secondary defense layer: Filter out any chunks that belong to unauthorized plans
        before fusion, parent expansion, or response generation.
        """
        authorized = AuthorizationService.get_authorized_plans(role)
        sanitized = []
        for c in chunks:
            pid = c.get("plan_id") or c.get("metadata", {}).get("plan_id")
            if pid in authorized:
                sanitized.append(c)
            else:
                logger.warning(f"Security filter caught unauthorized chunk from plan {pid} for role {role}")
        return sanitized

def get_current_user(request: Request) -> UserIdentity:
    """
    Extracts authenticated user identity from request.
    Priority 1: Bearer token or X-Session-Token validated against SQLite database.
    Priority 2: X-User-Role header (for backwards compatibility with existing test suites).
    Fails closed with 401 Unauthorized if neither is present or token is invalid.
    """
    # 1. Inspect Authorization Bearer token or X-Session-Token
    auth_header = request.headers.get("Authorization", "").strip()
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "X-Session-Token" in request.headers:
        token = request.headers["X-Session-Token"].strip()

    if token:
        session = sqlite_db.get_session(token)
        if not session:
            logger.warning("Invalid or expired session token presented.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication session. Please log in again."
            )
        # Derive trusted role strictly from SQLite record
        return UserIdentity(
            user_id=session["user_id"],
            role=session["effective_role"],
            full_name=session["full_name"] or "User",
            email=session["email"]
        )

    # Unauthenticated requests to any protected endpoint are rejected with 401
    logger.warning(f"Unauthenticated request to protected endpoint '{request.url.path}'.")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide a valid session token."
    )

def require_admin_user(request: Request) -> UserIdentity:
    """
    Enforces server-side administrator authorization.
    Returns HTTP 401 for unauthenticated requests,
    and HTTP 403 for authenticated non-administrators.
    """
    auth_header = request.headers.get("Authorization", "").strip()
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "X-Session-Token" in request.headers:
        token = request.headers["X-Session-Token"].strip()

    if not token:
        # Check if X-User-Role was provided by a non-admin
        if "X-User-Role" in request.headers:
            client_role = request.headers["X-User-Role"].lower().strip()
            sqlite_db.record_audit_event(
                action="admin_endpoint_forbidden",
                actor_id=request.headers.get("X-User-Id", "unknown"),
                actor_role=client_role,
                target_resource=str(request.url.path),
                outcome="FORBIDDEN",
                details={"reason": f"Role '{client_role}' lacks admin privileges"}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Administrator privileges required."
            )
        
        sqlite_db.record_audit_event(
            action="admin_endpoint_unauthorized",
            actor_id="anonymous",
            actor_role="none",
            target_resource=str(request.url.path),
            outcome="UNAUTHORIZED",
            details={"reason": "Missing authentication session token"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in as an administrator."
        )

    session = sqlite_db.get_session(token)
    if not session:
        sqlite_db.record_audit_event(
            action="admin_endpoint_unauthorized",
            actor_id="invalid_session",
            actor_role="none",
            target_resource=str(request.url.path),
            outcome="UNAUTHORIZED",
            details={"reason": "Expired or invalid session token"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again."
        )

    effective_role = session.get("effective_role", "").lower().strip()
    if effective_role != "admin":
        sqlite_db.record_audit_event(
            action="admin_endpoint_forbidden",
            actor_id=session.get("user_id"),
            actor_email=session.get("email"),
            actor_role=effective_role,
            target_resource=str(request.url.path),
            outcome="FORBIDDEN",
            details={"reason": f"Authenticated user has role '{effective_role}', not 'admin'"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrator privileges required."
        )

    return UserIdentity(
        user_id=session["user_id"],
        role="admin",
        full_name=session.get("full_name") or "Administrator",
        email=session.get("email")
    )
