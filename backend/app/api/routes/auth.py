from fastapi import APIRouter, HTTPException, Depends, Request, status
from backend.app.api.schemas.auth import (
    SignupRequest,
    LoginRequest,
    AuthResponse,
    UserPayload,
    UserProfileResponse
)
from backend.app.services.auth_service import (
    register_user,
    authenticate_user,
    logout_session,
    UserIdentity,
    get_current_user
)
from backend.app.db.sqlite_manager import sqlite_db
from backend.app.core.logging_config import logger

router = APIRouter(prefix="/auth", tags=["Authentication & User Management"])

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest):
    """
    Registers a new account securely.
    - Hashes password using bcrypt.
    - Role is derived server-side.
    - Returns session token and user profile without exposing sensitive credentials.
    """
    user_record, token, notice = register_user(
        email=req.email,
        password=req.password,
        requested_role=req.role,
        full_name=req.full_name
    )

    return AuthResponse(
        token=token,
        user=UserPayload(
            user_id=user_record["user_id"],
            email=user_record["email"],
            role=user_record["role"],
            full_name=user_record["full_name"],
            is_approved=bool(user_record["is_approved"]),
            requested_role=user_record["requested_role"]
        ),
        message=notice or "Registration successful."
    )

@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    """
    Authenticates email and password against SQLite store.
    Generates a secure session token and returns the authenticated user identity.
    """
    user_record, token = authenticate_user(
        email=req.email,
        password=req.password
    )

    return AuthResponse(
        token=token,
        user=UserPayload(
            user_id=user_record["user_id"],
            email=user_record["email"],
            role=user_record["effective_role"],
            full_name=user_record["full_name"],
            is_approved=bool(user_record["is_approved"]),
            requested_role=user_record["requested_role"]
        ),
        message="Login successful."
    )

@router.post("/logout")
def logout(request: Request):
    """
    Invalidates the active user session token.
    """
    auth_header = request.headers.get("Authorization", "").strip()
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "X-Session-Token" in request.headers:
        token = request.headers["X-Session-Token"].strip()

    if token:
        logout_session(token)

    return {"status": "SUCCESS", "message": "Session invalidated successfully."}

@router.get("/me", response_model=UserProfileResponse)
def get_me(user: UserIdentity = Depends(get_current_user)):
    """
    Retrieves profile and permissions for the currently authenticated session.
    """
    db_user = sqlite_db.get_user_by_id(user.user_id)
    if not db_user:
        # Fallback for dev / test identities
        return UserProfileResponse(
            user_id=user.user_id,
            email=user.email or f"{user.user_id}@test.local",
            role=user.role,
            full_name=user.full_name,
            is_approved=True,
            governance_status="active"
        )

    return UserProfileResponse(
        user_id=db_user["user_id"],
        email=db_user["email"],
        role=db_user["effective_role"],
        full_name=db_user["full_name"] or "User",
        is_approved=bool(db_user["is_approved"]),
        governance_status="active" if db_user["is_approved"] else "pending_verification",
        created_at=db_user["created_at"]
    )
