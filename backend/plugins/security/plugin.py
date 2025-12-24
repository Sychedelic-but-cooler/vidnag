"""
Security Headers Plugin
Adds security headers to all responses
"""

from typing import Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from backend.plugins.base import MiddlewarePlugin


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to responses"""

    def __init__(self, app: ASGIApp, headers: Dict[str, str]):
        super().__init__(app)
        self.headers = headers

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Add all configured security headers
        for header_name, header_value in self.headers.items():
            response.headers[header_name] = header_value

        return response


class SecurityPlugin(MiddlewarePlugin):
    """
    Security headers plugin

    Adds security headers to protect against common web vulnerabilities:
    - X-Frame-Options: Prevents clickjacking
    - X-Content-Type-Options: Prevents MIME sniffing
    - X-XSS-Protection: XSS filter for older browsers
    - Strict-Transport-Security: Forces HTTPS
    - Content-Security-Policy: Prevents XSS and injection
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    """

    @property
    def name(self) -> str:
        return "security"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Adds security headers to all HTTP responses"

    def validate_config(self) -> None:
        """Validate security headers configuration"""
        headers = self.config.get('headers', {})

        if not isinstance(headers, dict):
            raise ValueError("headers must be a dictionary")

        if not headers:
            raise ValueError("At least one security header must be configured")

        # Warn about missing critical headers
        critical_headers = [
            'X-Frame-Options',
            'X-Content-Type-Options',
            'Content-Security-Policy'
        ]

        for header in critical_headers:
            if header not in headers:
                self.log_warning(f"Critical security header '{header}' is not configured")

    def create_middleware(self, app: ASGIApp) -> BaseHTTPMiddleware:
        """Create security headers middleware"""
        headers = self.config.get('headers', {})
        return SecurityHeadersMiddleware(app, headers)

    def on_startup(self) -> None:
        """Log security headers on startup"""
        headers = self.config.get('headers', {})
        self.log_info(f"Security plugin active with {len(headers)} headers configured")


# Required export
PluginClass = SecurityPlugin
