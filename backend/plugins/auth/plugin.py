"""
Auth Plugin
JWT-based authentication middleware
"""

from typing import List, Optional, Dict, Any
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from backend.plugins.base import MiddlewarePlugin


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates JWT tokens

    Checks Authorization header for JWT tokens and validates them.
    Sets request.state.user if authenticated.

    ALL auth checks happen here on server side:
    - Token validation
    - User active status
    - Session validity
    - Admin status verification
    """

    def __init__(
        self,
        app: ASGIApp,
        exempt_paths: List[str],
        auth_service,
        db_manager
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths
        self.auth_service = auth_service
        self.db_manager = db_manager

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Check if path is exempt from authentication
        if self._is_exempt(path):
            return await call_next(request)

        # Get authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"error": "Authentication required"}
            )

        # Parse Bearer token
        try:
            scheme, token = auth_header.split(maxsplit=1)
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authorization scheme")
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid authorization header format"}
            )

        # Validate token and get user (ALL checks happen in auth service!)
        with self.db_manager.session_scope() as db:
            user = self.auth_service.verify_token(db, token)

            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid or expired token"}
                )

            # Set user in request state (server-verified data only!)
            request.state.user = user
            request.state.user_id = user.id
            request.state.is_admin = user.is_admin
            request.state.username = user.username

        # Continue processing
        return await call_next(request)

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from authentication"""
        for exempt in self.exempt_paths:
            if exempt.endswith('*'):
                # Prefix match
                if path.startswith(exempt[:-1]):
                    return True
            else:
                # Exact match
                if path == exempt:
                    return True

        return False


class AuthPlugin(MiddlewarePlugin):
    """
    JWT authentication plugin

    Validates JWT tokens and enforces authentication on protected routes.
    Public routes can be exempted via configuration.

    Protected by critical_plugins - cannot be disabled via web interface.
    """

    @property
    def name(self) -> str:
        return "auth"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "JWT-based authentication middleware"

    def validate_config(self) -> None:
        """Validate auth configuration"""
        # JWT secret comes from APP settings, not plugin config
        # This is a critical security setting

        exempt_paths = self.config.get('exempt_paths', [])
        if not isinstance(exempt_paths, list):
            raise ValueError("exempt_paths must be a list")

        # Ensure critical auth endpoints are never exempt
        protected_paths = ['/api/admin/', '/api/users/me']
        for path in protected_paths:
            for exempt in exempt_paths:
                if exempt.startswith(path) or path.startswith(exempt.rstrip('*')):
                    self.log_warning(
                        f"Sensitive path '{path}' may be in exempt list. "
                        "Ensure this is intentional."
                    )

    def initialize(self, app: FastAPI) -> None:
        """Initialize plugin - store auth service and db manager"""
        from backend.core.database import get_db
        from backend.core.settings import settings, SettingsLevel
        from backend.utils.jwt import JWTManager
        from backend.utils.auth_service import AuthService

        # Get database manager
        self.db_manager = get_db()

        # Create JWT manager
        secret_key = settings.get(SettingsLevel.APP, "security.secret_key")
        algorithm = settings.get(SettingsLevel.APP, "security.jwt_algorithm", "HS256")
        jwt_manager = JWTManager(secret_key, algorithm)

        # Create auth service
        self.auth_service = AuthService(jwt_manager, settings)

        # Store in app state for use by routes
        app.state.auth_service = self.auth_service
        app.state.jwt_manager = jwt_manager

    def get_middleware_class(self) -> type:
        """Return the middleware class"""
        return AuthMiddleware

    def get_middleware_kwargs(self) -> Dict[str, Any]:
        """Return middleware constructor kwargs"""
        # Get exempt paths from plugin config
        exempt_paths = self.config.get('exempt_paths', [
            '/api/auth/login',
            '/api/auth/register',
            '/api/auth/refresh',
            '/api/share/*',
            '/health',
            '/docs',
            '/openapi.json',
            '/'
        ])

        return {
            "exempt_paths": exempt_paths,
            "auth_service": self.auth_service,
            "db_manager": self.db_manager
        }

    def on_startup(self) -> None:
        """Log auth configuration on startup"""
        exempt_count = len(self.config.get('exempt_paths', []))
        self.log_info(f"Authentication enabled with {exempt_count} exempt paths")
        self.log_info("JWT token validation active")


# Required export
PluginClass = AuthPlugin
