"""
Vidnag Plugin System

Available Plugins:
- proxy: Configures IP extraction from reverse proxies
- auth: JWT-based authentication
- ratelimit: Request rate limiting per IP
- cors: Cross-Origin Resource Sharing
- security: Security headers
"""

from backend.plugins.base import Plugin, MiddlewarePlugin, RoutePlugin
from backend.plugins.manager import PluginManager

__all__ = [
    'Plugin',
    'MiddlewarePlugin',
    'RoutePlugin',
    'PluginManager'
]
