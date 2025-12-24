"""
Vidnag Logging System
Provides structured logging with rotation and browser debug streaming
"""

import logging
import json
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from collections import deque


class LogType(Enum):
    """Types of logs in the system"""
    ADMIN = "admin"         # Admin actions and changes
    USER = "user"           # User activity
    APPLICATION = "app"     # System events


class SensitiveFieldFilter(logging.Filter):
    """Filter to redact sensitive fields from log records"""

    def __init__(self, sensitive_fields: List[str]):
        super().__init__()
        self.sensitive_fields = [f.lower() for f in sensitive_fields]

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive fields from the log message"""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            msg_lower = record.msg.lower()
            for field in self.sensitive_fields:
                if field in msg_lower:
                    # Redact the field value
                    record.msg = self._redact_field(record.msg, field)
        return True

    def _redact_field(self, message: str, field: str) -> str:
        """Redact a specific field from the message"""
        # Simple redaction - can be enhanced with regex
        import re
        pattern = rf"{field}[=:]\s*['\"]?([^'\"\s,}}]+)"
        return re.sub(pattern, f"{field}=***REDACTED***", message, flags=re.IGNORECASE)


class BrowserLogHandler:
    """Handler for streaming logs to browser consoles"""

    def __init__(self):
        self.subscribers: Dict[int, deque] = {}  # user_id -> deque of messages
        self.max_buffer_size = 100

    def subscribe(self, user_id: int) -> None:
        """Subscribe a user to receive log messages"""
        if user_id not in self.subscribers:
            self.subscribers[user_id] = deque(maxlen=self.max_buffer_size)

    def unsubscribe(self, user_id: int) -> None:
        """Unsubscribe a user from log messages"""
        if user_id in self.subscribers:
            del self.subscribers[user_id]

    def emit(self, log_type: LogType, level: str, message: str, extra: Dict[str, Any]) -> None:
        """Emit a log message to all subscribers"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": log_type.value,
            "level": level,
            "message": message,
            "extra": extra
        }

        # Add to each subscriber's buffer
        for user_id, buffer in self.subscribers.items():
            buffer.append(log_entry)

    def get_messages(self, user_id: int, clear: bool = True) -> List[Dict[str, Any]]:
        """Get buffered messages for a user"""
        if user_id not in self.subscribers:
            return []

        messages = list(self.subscribers[user_id])
        if clear:
            self.subscribers[user_id].clear()

        return messages


class VidnagLogger:
    """Logger for a specific log type"""

    def __init__(
        self,
        log_type: LogType,
        log_dir: Path,
        retention_days: int,
        level: str,
        sensitive_fields: List[str],
        browser_handler: Optional[BrowserLogHandler] = None
    ):
        self.log_type = log_type
        self.logger = logging.getLogger(f"vidnag.{log_type.value}")
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.propagate = False
        self.browser_handler = browser_handler

        # Clear any existing handlers
        self.logger.handlers.clear()

        # Create log directory
        log_dir.mkdir(parents=True, exist_ok=True)

        # File handler with daily rotation
        log_file = log_dir / f"{log_type.value}.log"
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=retention_days,
            encoding='utf-8'
        )
        file_handler.suffix = "%Y-%m-%d"

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # Add sensitive field filter
        file_handler.addFilter(SensitiveFieldFilter(sensitive_fields))

        # Add handler
        self.logger.addHandler(file_handler)

        # Also log to console in debug mode
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(SensitiveFieldFilter(sensitive_fields))
        self.logger.addHandler(console_handler)

    def _emit_to_browser(self, level: str, message: str, extra: Dict[str, Any]) -> None:
        """Emit log to browser handler if available"""
        if self.browser_handler:
            self.browser_handler.emit(self.log_type, level, message, extra)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)
        self._emit_to_browser("DEBUG", message, kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        self.logger.info(message, extra=kwargs)
        self._emit_to_browser("INFO", message, kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)
        self._emit_to_browser("WARNING", message, kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message"""
        self.logger.error(message, extra=kwargs)
        self._emit_to_browser("ERROR", message, kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message"""
        self.logger.critical(message, extra=kwargs)
        self._emit_to_browser("CRITICAL", message, kwargs)


class LogManager:
    """Central logging manager for Vidnag"""

    def __init__(self, settings_manager):
        self.settings = settings_manager
        self.browser_handler = BrowserLogHandler()
        self._setup_loggers()

    def _setup_loggers(self) -> None:
        """Set up all log types"""
        from backend.core.settings import SettingsLevel

        # Get logging config
        retention_days = self.settings.get(
            SettingsLevel.ADMIN,
            "logging.retention_days",
            7
        )

        sensitive_fields = self.settings.get(
            SettingsLevel.ADMIN,
            "logging.sensitive_fields",
            ["password", "secret_key", "token"]
        )

        log_levels = self.settings.get(
            SettingsLevel.ADMIN,
            "logging.log_levels",
            {"admin": "INFO", "user": "INFO", "application": "INFO"}
        )

        # Create log directory
        log_dir = Path("logs")

        # Initialize loggers
        self.admin = VidnagLogger(
            LogType.ADMIN,
            log_dir,
            retention_days,
            log_levels.get("admin", "INFO"),
            sensitive_fields,
            self.browser_handler
        )

        self.user = VidnagLogger(
            LogType.USER,
            log_dir,
            retention_days,
            log_levels.get("user", "INFO"),
            sensitive_fields,
            self.browser_handler
        )

        self.app = VidnagLogger(
            LogType.APPLICATION,
            log_dir,
            retention_days,
            log_levels.get("application", "INFO"),
            sensitive_fields,
            self.browser_handler
        )

        self.app.info("Logging system initialized", version=self.settings.get_version())

    # Admin log methods
    def log_admin_action(
        self,
        action: str,
        admin_id: int,
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None
    ) -> None:
        """Log an admin action"""
        msg = f"Admin action: {action}"
        if target:
            msg += f" | target={target}"

        self.admin.info(
            msg,
            admin_id=admin_id,
            action=action,
            target=target,
            details=details or {},
            ip=ip
        )

    def log_admin_login(self, admin_id: int, username: str, ip: str, success: bool) -> None:
        """Log admin login attempt"""
        level = "info" if success else "warning"
        status = "SUCCESS" if success else "FAILED"

        getattr(self.admin, level)(
            f"Admin login {status}: {username}",
            admin_id=admin_id,
            username=username,
            ip=ip,
            success=success
        )

    def log_settings_change(
        self,
        admin_id: int,
        setting_path: str,
        old_value: Any,
        new_value: Any,
        ip: str
    ) -> None:
        """Log settings change"""
        self.admin.warning(
            f"Settings changed: {setting_path}",
            admin_id=admin_id,
            setting=setting_path,
            old_value=str(old_value)[:100],  # Limit length
            new_value=str(new_value)[:100],
            ip=ip
        )

    # User log methods
    def log_user_login(self, user_id: int, username: str, ip: str, success: bool) -> None:
        """Log user login attempt"""
        level = "info" if success else "warning"
        status = "SUCCESS" if success else "FAILED"

        getattr(self.user, level)(
            f"User login {status}: {username}",
            user_id=user_id,
            username=username,
            ip=ip,
            success=success
        )

    def log_user_action(
        self,
        action: str,
        user_id: int,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None
    ) -> None:
        """Log a user action"""
        msg = f"User action: {action}"
        if resource:
            msg += f" | resource={resource}"

        self.user.info(
            msg,
            user_id=user_id,
            action=action,
            resource=resource,
            details=details or {},
            ip=ip
        )

    def log_video_upload(self, user_id: int, filename: str, size: int, ip: str) -> None:
        """Log video upload"""
        self.user.info(
            f"Video uploaded: {filename}",
            user_id=user_id,
            filename=filename,
            size_bytes=size,
            ip=ip
        )

    def log_video_download(self, user_id: int, url: str, ip: str) -> None:
        """Log video download from URL"""
        self.user.info(
            f"Video download initiated: {url}",
            user_id=user_id,
            url=url,
            ip=ip
        )

    # Application log methods
    def log_startup(self, version: str, debug_mode: bool) -> None:
        """Log application startup"""
        self.app.info(
            f"Vidnag started - version {version}",
            version=version,
            debug_mode=debug_mode
        )

    def log_shutdown(self) -> None:
        """Log application shutdown"""
        self.app.info("Vidnag shutting down")

    def log_request(self, method: str, path: str, status_code: int, ip: str, user_id: Optional[int] = None) -> None:
        """Log HTTP request"""
        self.app.debug(
            f"{method} {path} - {status_code}",
            method=method,
            path=path,
            status=status_code,
            ip=ip,
            user_id=user_id
        )

    def log_video_processing(
        self,
        video_id: int,
        job_type: str,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log video processing job"""
        level = "info" if status in ["started", "completed"] else "error"

        getattr(self.app, level)(
            f"Video processing {status}: video_id={video_id} type={job_type}",
            video_id=video_id,
            job_type=job_type,
            status=status,
            details=details or {}
        )

    def log_error(self, error: Exception, context: str, **kwargs) -> None:
        """Log error with context"""
        self.app.error(
            f"Error in {context}: {str(error)}",
            context=context,
            error_type=type(error).__name__,
            error_message=str(error),
            **kwargs
        )

    def log_security_event(self, event_type: str, details: str, ip: str, severity: str = "warning") -> None:
        """Log security-related events"""
        level = getattr(self.app, severity.lower())
        level(
            f"Security event: {event_type}",
            event_type=event_type,
            details=details,
            ip=ip
        )

    # Browser debug methods
    def enable_browser_debug(self, user_id: int) -> None:
        """Enable browser debug for a user"""
        from backend.core.settings import SettingsLevel

        # Check if browser debug is enabled in settings
        browser_debug = self.settings.get(
            SettingsLevel.ADMIN,
            "logging.browser_debug",
            {}
        )

        if not browser_debug.get("enabled", False):
            raise PermissionError("Browser debug is not enabled in admin settings")

        # Check if user is allowed
        allowed_users = browser_debug.get("allowed_user_ids", [])
        if allowed_users and user_id not in allowed_users:
            raise PermissionError(f"User {user_id} is not allowed to use browser debug")

        self.browser_handler.subscribe(user_id)
        self.admin.info(f"Browser debug enabled for user {user_id}", user_id=user_id)

    def disable_browser_debug(self, user_id: int) -> None:
        """Disable browser debug for a user"""
        self.browser_handler.unsubscribe(user_id)
        self.admin.info(f"Browser debug disabled for user {user_id}", user_id=user_id)

    def get_browser_logs(self, user_id: int, clear: bool = True) -> List[Dict[str, Any]]:
        """Get browser debug logs for a user"""
        return self.browser_handler.get_messages(user_id, clear)

    def reload_config(self) -> None:
        """Reload logging configuration from settings"""
        self.admin.info("Reloading logging configuration")
        self._setup_loggers()


# Initialize global logger instance (will be set by main app)
logger: Optional[LogManager] = None


def get_logger() -> LogManager:
    """Get the global logger instance"""
    if logger is None:
        raise RuntimeError("Logger not initialized. Call init_logger() first.")
    return logger


def init_logger(settings_manager) -> LogManager:
    """Initialize the global logger"""
    global logger
    logger = LogManager(settings_manager)
    return logger
