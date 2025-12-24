"""
Authentication Routes
Login, register, logout, refresh token endpoints
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.ip_extraction import get_client_ip
from backend.core.logging import get_logger
from backend.models import User
from backend.utils.auth_service import AuthService, LoginFailedError, RegistrationError


router = APIRouter(prefix="/api/auth", tags=["authentication"])


# === Request/Response Models ===

class RegisterRequest(BaseModel):
    """Registration request"""
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    """Login request"""
    username: str  # Can be username or email
    password: str


class RefreshRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class AuthResponse(BaseModel):
    """Authentication response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


# === Dependencies ===

def get_auth_service(request: Request) -> AuthService:
    """Get auth service from app state"""
    return request.app.state.auth_service


def get_db_session():
    """Database session dependency for FastAPI routes"""
    yield from get_db().get_dependency()


# === Routes ===

@router.post("/register", response_model=AuthResponse)
def register(
    data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user

    Creates user account and returns JWT tokens.
    Only username stored in localStorage (via JWT).
    """
    logger = get_logger()
    ip = get_client_ip(request)

    try:
        # Register user (all validation happens server-side!)
        user, access_token, refresh_token = auth_service.register_user(
            db,
            username=data.username,
            email=data.email,
            password=data.password,
            is_admin=False  # Never allow admin registration via API
        )

        # Log registration
        logger.log_user_action(
            action="user_registered",
            user_id=user.id,
            details={"username": user.username, "email": user.email},
            ip=ip
        )

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "storage_used": user.storage_used,
                "storage_quota": user.storage_quota
            }
        )

    except RegistrationError as e:
        # Return specific error for registration
        logger.log_user_action(
            action="registration_failed",
            user_id=None,
            details={"username": data.username, "reason": str(e)},
            ip=ip
        )
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResponse)
def login(
    data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login user

    Returns JWT tokens if credentials are valid.
    Generic error message on failure (security!).

    Client stores JWT in localStorage.
    Server validates everything:
    - Password correctness
    - Account active status
    - Account lockout status (future)
    """
    logger = get_logger()
    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")

    try:
        # Attempt login (all checks happen server-side!)
        user, access_token, refresh_token = auth_service.login(
            db,
            username=data.username,
            password=data.password,
            ip_address=ip,
            user_agent=user_agent
        )

        # Log successful login
        logger.log_user_login(
            user_id=user.id,
            username=user.username,
            ip=ip,
            success=True
        )

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "storage_used": user.storage_used,
                "storage_quota": user.storage_quota,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        )

    except LoginFailedError:
        # Generic error - don't leak information!
        logger.log_user_login(
            user_id=None,
            username=data.username,
            ip=ip,
            success=False
        )

        # Log security event
        logger.log_security_event(
            event_type="failed_login",
            details=f"Failed login attempt for: {data.username}",
            ip=ip,
            severity="warning"
        )

        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"  # Generic message!
        )


@router.post("/refresh", response_model=AuthResponse)
def refresh_token(
    data: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token

    Returns new access and refresh tokens.
    """
    logger = get_logger()
    ip = get_client_ip(request)

    result = auth_service.refresh_access_token(db, data.refresh_token)

    if not result:
        logger.log_security_event(
            event_type="invalid_refresh_token",
            details="Refresh token validation failed",
            ip=ip,
            severity="warning"
        )
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access_token, new_refresh_token = result

    # Get user from token to return user info
    from backend.utils.jwt import JWTManager
    jwt_manager = request.app.state.jwt_manager
    payload = jwt_manager.verify_token(new_access_token)

    if not payload:
        raise HTTPException(status_code=401, detail="Token generation failed")

    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return AuthResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        }
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout user (revoke current session)

    Requires valid JWT token in Authorization header.
    """
    logger = get_logger()
    ip = get_client_ip(request)

    # Get token from header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        _, token = auth_header.split(maxsplit=1)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    # Get user info before logout
    user = auth_service.verify_token(db, token)
    if user:
        user_id = user.id
        username = user.username
    else:
        user_id = None
        username = "unknown"

    # Revoke session
    success = auth_service.logout(db, token)

    if success:
        logger.log_user_action(
            action="user_logout",
            user_id=user_id,
            details={"username": username},
            ip=ip
        )
        return MessageResponse(message="Logged out successfully")
    else:
        return MessageResponse(message="Session already invalidated")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all_sessions(
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout from all devices (revoke all sessions)

    Requires valid JWT token in Authorization header.
    Useful if user suspects account compromise.
    """
    logger = get_logger()
    ip = get_client_ip(request)

    # Get user from request state (set by auth middleware)
    if not hasattr(request.state, 'user'):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = request.state.user

    # Revoke all sessions for this user
    count = auth_service.logout_all_sessions(db, user.id)

    logger.log_user_action(
        action="user_logout_all",
        user_id=user.id,
        details={"username": user.username, "sessions_revoked": count},
        ip=ip
    )

    return MessageResponse(
        message=f"Logged out from {count} device(s) successfully"
    )


@router.get("/me")
def get_current_user(request: Request):
    """
    Get current authenticated user

    Returns user info from server-verified JWT token.
    Requires authentication.
    """
    # User is set by auth middleware
    if not hasattr(request.state, 'user'):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = request.state.user

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "storage_used": user.storage_used,
        "storage_quota": user.storage_quota,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "login_count": user.login_count,
        "email_verified": user.email_verified
    }
