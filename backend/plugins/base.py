"""
Vidnag Plugin Base Classes
Base classes for all plugins in the system
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class Plugin(ABC):
    """Base class for all Vidnag plugins"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.priority = config.get('priority', 100)
        self.logger = None  # Will be set by plugin manager

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass

    @property
    def description(self) -> str:
        """Plugin description"""
        return "No description provided"

    @property
    def dependencies(self) -> List[str]:
        """List of plugin names this depends on"""
        return []

    def initialize(self, app: FastAPI) -> None:
        """
        Called when plugin is loaded during application startup
        Use this to set up resources, validate config, etc.
        """
        pass

    def on_startup(self) -> None:
        """Called on application startup (after all plugins initialized)"""
        pass

    def on_shutdown(self) -> None:
        """Called on application shutdown"""
        pass

    def get_middleware(self) -> Optional[tuple]:
        """
        Return middleware class and kwargs for FastAPI registration

        Returns:
            None or tuple of (middleware_class, kwargs_dict)

        Example:
            return (MyMiddleware, {"config": self.config})
        """
        return None

    def register_routes(self, app: FastAPI) -> None:
        """Register additional API routes if needed"""
        pass

    def validate_config(self) -> None:
        """
        Validate plugin configuration
        Raise ValueError if config is invalid
        """
        pass

    def set_logger(self, logger) -> None:
        """Set the logger instance for this plugin"""
        self.logger = logger

    def log_info(self, message: str, **kwargs) -> None:
        """Log info message"""
        if self.logger:
            self.logger.app.info(f"[{self.name}] {message}", **kwargs)

    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        if self.logger:
            self.logger.app.warning(f"[{self.name}] {message}", **kwargs)

    def log_error(self, message: str, **kwargs) -> None:
        """Log error message"""
        if self.logger:
            self.logger.app.error(f"[{self.name}] {message}", **kwargs)

    def __repr__(self) -> str:
        return f"<Plugin:{self.name} v{self.version} enabled={self.enabled}>"


class MiddlewarePlugin(Plugin):
    """Base class for plugins that provide middleware"""

    @abstractmethod
    def get_middleware_class(self) -> type:
        """Return the middleware class to register"""
        pass

    @abstractmethod
    def get_middleware_kwargs(self) -> Dict[str, Any]:
        """Return kwargs for middleware constructor (excluding 'app')"""
        pass

    def get_middleware(self) -> Optional[tuple]:
        """Return middleware class and kwargs for registration"""
        return (self.get_middleware_class(), self.get_middleware_kwargs())


class RoutePlugin(Plugin):
    """Base class for plugins that register routes"""

    @abstractmethod
    def setup_routes(self, app: FastAPI) -> None:
        """Set up plugin routes"""
        pass

    def register_routes(self, app: FastAPI) -> None:
        """Register routes (called by plugin manager)"""
        self.setup_routes(app)
