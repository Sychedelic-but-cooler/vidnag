"""
CORS Plugin
Handles Cross-Origin Resource Sharing
"""

from typing import List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from backend.plugins.base import MiddlewarePlugin


class CORSMiddleware(BaseHTTPMiddleware):
    """Middleware that handles CORS"""

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: List[str],
        allow_methods: List[str],
        allow_headers: List[str],
        allow_credentials: bool,
        max_age: int
    ):
        super().__init__(app)
        self.allow_origins = allow_origins
        self.allow_methods = allow_methods
        self.allow_headers = allow_headers
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next) -> Response:
        # Handle preflight requests
        if request.method == "OPTIONS":
            return self._build_preflight_response(request)

        # Process normal request
        response = await call_next(request)

        # Add CORS headers to response
        self._add_cors_headers(request, response)

        return response

    def _build_preflight_response(self, request: Request) -> Response:
        """Build response for OPTIONS preflight request"""
        response = Response(status_code=200)
        self._add_cors_headers(request, response)
        return response

    def _add_cors_headers(self, request: Request, response: Response) -> None:
        """Add CORS headers to response"""
        origin = request.headers.get("origin")

        # Check if origin is allowed
        if origin and self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin

            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"

            if request.method == "OPTIONS":
                # Preflight response
                response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)

                if self.allow_headers:
                    if "*" in self.allow_headers:
                        # Allow all headers
                        requested_headers = request.headers.get("access-control-request-headers")
                        if requested_headers:
                            response.headers["Access-Control-Allow-Headers"] = requested_headers
                    else:
                        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)

                response.headers["Access-Control-Max-Age"] = str(self.max_age)

    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed"""
        if "*" in self.allow_origins:
            return True

        return origin in self.allow_origins


class CORSPlugin(MiddlewarePlugin):
    """
    CORS (Cross-Origin Resource Sharing) plugin

    Allows web applications from different origins to access the API.
    Essential for frontend applications hosted on different domains.
    """

    @property
    def name(self) -> str:
        return "cors"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Handles Cross-Origin Resource Sharing (CORS)"

    def validate_config(self) -> None:
        """Validate CORS configuration"""
        allow_origins = self.config.get('allow_origins', [])
        if not isinstance(allow_origins, list):
            raise ValueError("allow_origins must be a list")

        if not allow_origins:
            raise ValueError("At least one origin must be specified")

        allow_methods = self.config.get('allow_methods', [])
        if not isinstance(allow_methods, list):
            raise ValueError("allow_methods must be a list")

        allow_headers = self.config.get('allow_headers', [])
        if not isinstance(allow_headers, list):
            raise ValueError("allow_headers must be a list")

        # Warn about wildcard origins with credentials
        if "*" in allow_origins and self.config.get('allow_credentials', False):
            self.log_warning(
                "Using wildcard origin (*) with allow_credentials=true is not secure. "
                "Specify explicit origins instead."
            )

    def create_middleware(self, app: ASGIApp) -> BaseHTTPMiddleware:
        """Create CORS middleware"""
        return CORSMiddleware(
            app,
            allow_origins=self.config.get('allow_origins', []),
            allow_methods=self.config.get('allow_methods', ['GET', 'POST']),
            allow_headers=self.config.get('allow_headers', []),
            allow_credentials=self.config.get('allow_credentials', False),
            max_age=self.config.get('max_age', 600)
        )

    def on_startup(self) -> None:
        """Log CORS configuration on startup"""
        origins = self.config.get('allow_origins', [])
        methods = self.config.get('allow_methods', [])
        self.log_info(
            f"CORS enabled: {len(origins)} origins, methods: {', '.join(methods)}"
        )


# Required export
PluginClass = CORSPlugin
