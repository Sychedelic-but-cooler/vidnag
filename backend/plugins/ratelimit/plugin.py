"""
Rate Limit Plugin
Prevents abuse by limiting request rates per IP
"""

from typing import Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from backend.plugins.base import MiddlewarePlugin
from backend.core.ip_extraction import get_client_ip


class RateLimiter:
    """
    Rate limiter using sliding window algorithm

    Tracks requests per IP address and enforces limits.
    """

    def __init__(self):
        # Store: {ip: [(timestamp, path), ...]}
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())

    def parse_limit(self, limit_str: str) -> Tuple[int, timedelta]:
        """
        Parse limit string like '100/hour' into (count, duration)

        Returns:
            Tuple of (max_requests, time_window)
        """
        count_str, period = limit_str.split('/')
        count = int(count_str)

        periods = {
            'second': timedelta(seconds=1),
            'minute': timedelta(minutes=1),
            'hour': timedelta(hours=1),
            'day': timedelta(days=1)
        }

        if period not in periods:
            raise ValueError(f"Invalid period: {period}. Must be one of: {list(periods.keys())}")

        return (count, periods[period])

    def is_allowed(
        self,
        ip: str,
        path: str,
        limit: Tuple[int, timedelta]
    ) -> Tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit

        Args:
            ip: Client IP address
            path: Request path
            limit: (max_requests, time_window) tuple

        Returns:
            Tuple of (allowed, remaining, reset_seconds)
        """
        max_requests, time_window = limit
        now = datetime.now()
        window_start = now - time_window

        # Clean old requests outside the window
        self.requests[ip] = deque(
            [(ts, p) for ts, p in self.requests[ip] if ts > window_start]
        )

        # Count requests in current window
        current_count = len(self.requests[ip])

        if current_count >= max_requests:
            # Rate limit exceeded
            # Calculate when the oldest request will expire
            if self.requests[ip]:
                oldest = self.requests[ip][0][0]
                reset_seconds = int((oldest + time_window - now).total_seconds())
            else:
                reset_seconds = int(time_window.total_seconds())

            return (False, 0, reset_seconds)

        # Allow request and record it
        self.requests[ip].append((now, path))
        remaining = max_requests - current_count - 1

        return (True, remaining, int(time_window.total_seconds()))

    def cleanup_old_entries(self, max_age: timedelta = timedelta(hours=24)) -> None:
        """Remove old IP entries to prevent memory bloat"""
        cutoff = datetime.now() - max_age
        ips_to_remove = []

        for ip, requests in self.requests.items():
            if not requests or requests[-1][0] < cutoff:
                ips_to_remove.append(ip)

        for ip in ips_to_remove:
            del self.requests[ip]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces rate limits"""

    def __init__(
        self,
        app: ASGIApp,
        global_limit: str,
        path_limits: Dict[str, str]
    ):
        super().__init__(app)
        self.limiter = RateLimiter()
        self.global_limit = self.limiter.parse_limit(global_limit)
        self.path_limits = {
            path: self.limiter.parse_limit(limit)
            for path, limit in path_limits.items()
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        # Get client IP (set by IP extraction middleware)
        ip = get_client_ip(request)
        path = request.url.path

        # Find applicable limit (specific path or global)
        limit = self._get_limit_for_path(path)

        # Check rate limit
        allowed, remaining, reset = self.limiter.is_allowed(ip, path, limit)

        if not allowed:
            # Rate limit exceeded
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Try again in {reset} seconds.",
                    "retry_after": reset
                },
                headers={
                    "X-RateLimit-Limit": str(limit[0]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                    "Retry-After": str(reset)
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit[0])
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)

        return response

    def _get_limit_for_path(self, path: str) -> Tuple[int, timedelta]:
        """Get rate limit for a specific path"""
        # Check for exact match first
        if path in self.path_limits:
            return self.path_limits[path]

        # Check for prefix matches
        for pattern, limit in self.path_limits.items():
            if path.startswith(pattern.rstrip('*')):
                return limit

        # Use global limit
        return self.global_limit


class RateLimitPlugin(MiddlewarePlugin):
    """
    Rate limiting plugin

    Prevents abuse by limiting request rates per IP address.
    Uses sliding window algorithm for accurate rate limiting.

    Adds headers to responses:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Requests remaining in window
    - X-RateLimit-Reset: Seconds until window resets
    """

    @property
    def name(self) -> str:
        return "ratelimit"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Rate limiting to prevent abuse"

    def validate_config(self) -> None:
        """Validate rate limit configuration"""
        global_limit = self.config.get('global_limit')
        if not global_limit:
            raise ValueError("global_limit must be specified")

        # Validate format
        try:
            limiter = RateLimiter()
            limiter.parse_limit(global_limit)
        except Exception as e:
            raise ValueError(f"Invalid global_limit format: {e}")

        # Validate path-specific limits
        path_limits = self.config.get('upload_limit'), self.config.get('download_limit'), self.config.get('auth_limit')
        for limit in path_limits:
            if limit:
                try:
                    limiter.parse_limit(limit)
                except Exception as e:
                    raise ValueError(f"Invalid limit format: {e}")

    def create_middleware(self, app: ASGIApp) -> BaseHTTPMiddleware:
        """Create rate limit middleware"""
        global_limit = self.config.get('global_limit', '100/hour')

        # Build path-specific limits
        path_limits = {}

        if self.config.get('upload_limit'):
            path_limits['/api/videos/upload'] = self.config['upload_limit']

        if self.config.get('download_limit'):
            path_limits['/api/videos/download'] = self.config['download_limit']

        if self.config.get('auth_limit'):
            path_limits['/api/auth/'] = self.config['auth_limit']

        if self.config.get('processing_limit'):
            path_limits['/api/videos/process'] = self.config['processing_limit']

        return RateLimitMiddleware(app, global_limit, path_limits)

    def on_startup(self) -> None:
        """Log rate limit configuration on startup"""
        global_limit = self.config.get('global_limit', '100/hour')
        self.log_info(f"Rate limiting enabled: global={global_limit}")


# Required export
PluginClass = RateLimitPlugin
