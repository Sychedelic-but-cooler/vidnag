"""
FastAPI Dependencies
Reusable dependencies for routes
"""

from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models import User


def get_db_session() -> Session:
    """
    Get database session dependency

    Usage:
        @app.get("/endpoint")
        def my_endpoint(db: Session = Depends(get_db_session)):
            # Use db session
    """
    db_manager = get_db()
    yield from db_manager.get_dependency()


def get_current_user(request: Request) -> User:
    """
    Get current authenticated user from request

    Requires auth middleware to have run and set request.state.user.
    Use this dependency on protected routes.

    Usage:
        @app.get("/protected")
        def protected_endpoint(user: User = Depends(get_current_user)):
            # User is authenticated
            return {"user_id": user.id}

    Returns:
        User: Authenticated user from database

    Raises:
        HTTPException: 401 if not authenticated
    """
    if not hasattr(request.state, 'user') or not request.state.user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    return request.state.user


def get_current_admin(request: Request, user: User = Depends(get_current_user)) -> User:
    """
    Get current authenticated admin user

    Requires user to be authenticated AND have admin privileges.
    Server-side check of admin status.

    Usage:
        @app.get("/admin/endpoint")
        def admin_endpoint(admin: User = Depends(get_current_admin)):
            # User is authenticated AND is admin
            return {"admin_id": admin.id}

    Returns:
        User: Authenticated admin user

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin
    """
    # Check admin status (server-side verification!)
    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )

    return user


def get_optional_user(request: Request) -> User | None:
    """
    Get current user if authenticated, None otherwise

    Use this for endpoints that work for both authenticated and anonymous users,
    but provide different functionality based on authentication status.

    Usage:
        @app.get("/optional")
        def optional_endpoint(user: User | None = Depends(get_optional_user)):
            if user:
                return {"authenticated": True, "user_id": user.id}
            else:
                return {"authenticated": False}

    Returns:
        User | None: User if authenticated, None otherwise
    """
    if hasattr(request.state, 'user') and request.state.user:
        return request.state.user
    return None
