"""
Vidnag Core IP Extraction
Always-active IP parsing for logging and security

This is NOT a plugin - it's a core component that always runs.
The proxy plugin can configure which headers to trust, but IP extraction
itself is always active.
"""

from typing import Optional, List
from ipaddress import ip_address, ip_network, IPv4Address, IPv6Address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class IPExtractor:
    """
    Core IP extraction logic

    This extracts the client's true IP address for logging and security.
    Works with or without reverse proxies.
    """

    def __init__(
        self,
        trusted_proxies: Optional[List[str]] = None,
        proxy_headers: Optional[List[str]] = None
    ):
        """
        Initialize IP extractor

        Args:
            trusted_proxies: List of trusted proxy IP addresses/networks
            proxy_headers: List of headers to check for real IP
        """
        self.trusted_networks = []
        if trusted_proxies:
            for proxy in trusted_proxies:
                try:
                    self.trusted_networks.append(ip_network(proxy, strict=False))
                except ValueError:
                    # Invalid network, skip
                    pass

        self.proxy_headers = proxy_headers or [
            "X-Forwarded-For",
            "X-Real-IP",
            "CF-Connecting-IP"  # Cloudflare
        ]

    def extract_ip(self, request: Request) -> str:
        """
        Extract the real client IP from the request

        Returns:
            str: The client's IP address
        """
        # Get direct connection IP
        if not request.client:
            return "unknown"

        direct_ip = request.client.host

        # If no trusted proxies configured, use direct IP
        if not self.trusted_networks:
            return direct_ip

        # Check if request comes from trusted proxy
        if not self._is_trusted_proxy(direct_ip):
            # Not from trusted proxy, use direct IP
            return direct_ip

        # Request is from trusted proxy, check headers
        real_ip = self._extract_from_headers(request)

        # If we found a valid IP in headers, use it; otherwise use direct IP
        return real_ip if real_ip else direct_ip

    def _is_trusted_proxy(self, ip_str: str) -> bool:
        """Check if IP is from a trusted proxy"""
        try:
            addr = ip_address(ip_str)
            return any(addr in network for network in self.trusted_networks)
        except ValueError:
            return False

    def _extract_from_headers(self, request: Request) -> Optional[str]:
        """Extract IP from proxy headers"""
        for header in self.proxy_headers:
            if header in request.headers:
                # Get the header value
                value = request.headers[header]

                # X-Forwarded-For can be comma-separated (client, proxy1, proxy2)
                # We want the leftmost (original client) IP
                if ',' in value:
                    value = value.split(',')[0].strip()

                # Validate it's a valid IP
                if self._is_valid_ip(value):
                    return value

        return None

    def _is_valid_ip(self, ip_str: str) -> bool:
        """Check if string is a valid IP address"""
        try:
            ip_address(ip_str)
            return True
        except ValueError:
            return False


class IPExtractionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts and stores client IP in request state

    This runs before all other middleware and plugins.
    The IP is stored in request.state.client_ip for use by:
    - Logging
    - Rate limiting
    - Security checks
    - Audit logs
    """

    def __init__(self, app, extractor: IPExtractor):
        super().__init__(app)
        self.extractor = extractor

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract real client IP
        client_ip = self.extractor.extract_ip(request)

        # Store in request state for use by other middleware/routes
        request.state.client_ip = client_ip

        # Also store in request scope for easy access
        request.scope['client_ip'] = client_ip

        # Continue processing
        response = await call_next(request)

        # Optionally add IP to response headers (for debugging)
        # response.headers["X-Client-IP"] = client_ip

        return response


def get_client_ip(request: Request) -> str:
    """
    Helper function to get client IP from request

    Usage in routes:
        @app.get("/api/endpoint")
        def my_endpoint(request: Request):
            ip = get_client_ip(request)
            logger.log_request(..., ip=ip)
    """
    return getattr(request.state, 'client_ip', request.client.host if request.client else 'unknown')


# Documentation for IP extraction
"""
IP Extraction Strategy
======================

Without Reverse Proxy:
    Internet → Vidnag
    Use: Direct connection IP

With Reverse Proxy (unconfigured):
    Internet → Nginx → Vidnag
    Use: Direct connection IP (Nginx's IP)
    Result: All requests appear from Nginx
    Solution: Configure proxy plugin

With Reverse Proxy (configured):
    Internet → Nginx → Vidnag
    Nginx adds: X-Forwarded-For: <client-ip>
    Vidnag checks: Is request from trusted proxy? (Nginx)
    If yes: Use X-Forwarded-For header
    If no: Use direct IP (security)

Multiple Proxies:
    Internet → Cloudflare → Nginx → Vidnag
    Headers: X-Forwarded-For: client, proxy1, proxy2
    Use: Leftmost IP (original client)

Security:
    - Only trust headers from known proxies
    - Validate all IP addresses
    - Fallback to direct IP if invalid
    - Prevent IP spoofing

Configuration:
    Proxy plugin (settings/admin.json):
    {
      "proxy": {
        "enabled": true,
        "trusted_proxies": [
          "127.0.0.1",        // localhost
          "10.0.0.0/8",       // private networks
          "172.16.0.0/12",
          "192.168.0.0/16"
        ],
        "headers": [
          "X-Forwarded-For",  // Standard
          "X-Real-IP",        // Nginx
          "CF-Connecting-IP"  // Cloudflare
        ]
      }
    }

Usage in Code:
    from backend.core.ip_extraction import get_client_ip

    @app.get("/api/users")
    def list_users(request: Request):
        ip = get_client_ip(request)
        logger.log_request("GET", "/api/users", ip=ip)

    # IP is automatically available in request.state.client_ip
"""
