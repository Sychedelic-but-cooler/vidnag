"""
Vidnag Settings Manager
Manages configuration files with security levels
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
import jsonschema


class SettingsLevel(Enum):
    """Security classification of settings"""
    APP = "app"       # High-risk: core configuration
    ADMIN = "admin"   # Medium-risk: operational settings
    USER = "user"     # Low-risk: user preferences


class SettingsManager:
    """Manages configuration files with security levels"""

    def __init__(self, settings_dir: str = "settings"):
        self.settings_dir = Path(settings_dir)
        self.settings: Dict[SettingsLevel, Dict[str, Any]] = {}
        self._load_all()
        self._validate_permissions()

    def _load_all(self) -> None:
        """Load all configuration files"""
        for level in SettingsLevel:
            config_file = self.settings_dir / f"{level.value}.json"
            default_file = self.settings_dir / "defaults" / f"{level.value}.default.json"

            # Load from file or default
            if config_file.exists():
                with open(config_file, 'r') as f:
                    self.settings[level] = json.load(f)
            elif default_file.exists():
                with open(default_file, 'r') as f:
                    self.settings[level] = json.load(f)
                # Create config file from default
                self._save(level, self.settings[level])
                print(f"Created {level.value}.json from default template")
            else:
                raise FileNotFoundError(
                    f"No config or default found for {level.value}"
                )

            # Validate against schema
            self._validate_schema(level)

    def _validate_schema(self, level: SettingsLevel) -> None:
        """Validate settings against JSON schema"""
        schema_file = self.settings_dir / "schema" / f"{level.value}.schema.json"

        if schema_file.exists():
            with open(schema_file, 'r') as f:
                schema = json.load(f)

            try:
                jsonschema.validate(self.settings[level], schema)
            except jsonschema.ValidationError as e:
                raise ValueError(
                    f"Invalid {level.value} settings: {e.message}"
                )

    def _validate_permissions(self) -> None:
        """Ensure proper file permissions"""
        required_perms = {
            SettingsLevel.APP: 0o600,    # rw-------
            SettingsLevel.ADMIN: 0o640,  # rw-r-----
            SettingsLevel.USER: 0o644    # rw-r--r--
        }

        for level, required in required_perms.items():
            config_file = self.settings_dir / f"{level.value}.json"
            if config_file.exists():
                current = os.stat(config_file).st_mode & 0o777
                if current != required:
                    print(
                        f"WARNING: {level.value}.json has permissions {oct(current)}, "
                        f"should be {oct(required)}. Run: chmod {oct(required)[-3:]} {config_file}"
                    )

    def get(self, level: SettingsLevel, path: str, default: Any = None) -> Any:
        """
        Get a setting value using dot notation
        Example: get(SettingsLevel.APP, "database.host")
        """
        keys = path.split('.')
        value = self.settings.get(level, {})

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default

        return value if value is not None else default

    def set(self, level: SettingsLevel, path: str, value: Any, admin_user_id: Optional[int] = None) -> None:
        """
        Set a setting value using dot notation
        Only allows modification of ADMIN and USER settings
        """
        if level == SettingsLevel.APP:
            raise PermissionError(
                "Cannot modify APP settings at runtime. "
                "Edit settings/app.json manually and restart."
            )

        # Validate critical plugin protection for ADMIN level
        if level == SettingsLevel.ADMIN:
            self._validate_admin_change(path, value)

        keys = path.split('.')
        settings = self.settings[level]

        # Navigate to parent
        for key in keys[:-1]:
            if key not in settings:
                settings[key] = {}
            settings = settings[key]

        # Store old value for logging
        old_value = settings.get(keys[-1])

        # Set value
        settings[keys[-1]] = value

        # Validate entire config after change
        self._validate_schema(level)

        # Save to file
        self._save(level, self.settings[level])

        # Log the change
        print(
            f"ADMIN_CHANGE: user_id={admin_user_id} level={level.value} "
            f"setting={path} old={old_value} new={value}"
        )

    def _validate_admin_change(self, path: str, value: Any) -> None:
        """Validate admin setting changes for security"""
        # Get critical plugins from APP settings
        critical_plugins = self.get(
            SettingsLevel.APP,
            "security.critical_plugins",
            ["auth", "security"]
        )

        # Prevent disabling critical plugins
        if path == "plugins.disabled":
            if isinstance(value, list):
                for plugin in critical_plugins:
                    if plugin in value:
                        raise PermissionError(
                            f"Cannot disable critical plugin '{plugin}'. "
                            f"Edit settings/app.json manually to disable."
                        )

        # Prevent removing critical plugins from enabled list
        if path == "plugins.enabled":
            if isinstance(value, list):
                for plugin in critical_plugins:
                    if plugin not in value:
                        raise PermissionError(
                            f"Cannot remove critical plugin '{plugin}' from enabled list. "
                            f"Edit settings/app.json manually to disable."
                        )

        # Prevent dangerous combinations
        if path == "ratelimit.enabled" and value is False:
            auth_enabled = "auth" in self.get(
                SettingsLevel.ADMIN,
                "plugins.enabled",
                []
            )
            if not auth_enabled:
                raise ValueError(
                    "Cannot disable rate limiting when auth plugin is not enabled. "
                    "This would leave the system vulnerable to abuse."
                )

    def _save(self, level: SettingsLevel, data: Dict[str, Any]) -> None:
        """Save settings to file"""
        config_file = self.settings_dir / f"{level.value}.json"

        # Create backup for ADMIN settings
        if level == SettingsLevel.ADMIN and config_file.exists():
            self._create_backup(config_file)

        # Write settings
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Set proper permissions
        if level == SettingsLevel.APP:
            os.chmod(config_file, 0o600)
        elif level == SettingsLevel.ADMIN:
            os.chmod(config_file, 0o640)
        else:
            os.chmod(config_file, 0o644)

    def _create_backup(self, config_file: Path) -> None:
        """Create timestamped backup of config file"""
        backup_dir = self.settings_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{config_file.stem}.{timestamp}.json"

        shutil.copy(config_file, backup_file)

        # Keep only last 10 backups
        self._cleanup_old_backups(backup_dir, keep=10)

    def _cleanup_old_backups(self, backup_dir: Path, keep: int = 10) -> None:
        """Keep only the most recent N backups"""
        backups = sorted(backup_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)

        # Remove oldest backups if we have more than 'keep'
        if len(backups) > keep:
            for old_backup in backups[:-keep]:
                old_backup.unlink()

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for a specific plugin"""
        # Check if plugin is enabled
        enabled_plugins = self.get(
            SettingsLevel.ADMIN,
            "plugins.enabled",
            []
        )
        disabled_plugins = self.get(
            SettingsLevel.ADMIN,
            "plugins.disabled",
            []
        )

        if plugin_name not in enabled_plugins or plugin_name in disabled_plugins:
            return {"enabled": False}

        # Gather config from admin settings
        plugin_config = self.get(
            SettingsLevel.ADMIN,
            plugin_name,
            {}
        )

        # Ensure it's a dict and add enabled flag
        if not isinstance(plugin_config, dict):
            plugin_config = {}

        plugin_config["enabled"] = True
        return plugin_config

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled"""
        enabled = self.get(SettingsLevel.ADMIN, "plugins.enabled", [])
        disabled = self.get(SettingsLevel.ADMIN, "plugins.disabled", [])
        return plugin_name in enabled and plugin_name not in disabled

    def reload(self, level: Optional[SettingsLevel] = None) -> None:
        """Reload settings from disk"""
        if level:
            config_file = self.settings_dir / f"{level.value}.json"
            with open(config_file, 'r') as f:
                self.settings[level] = json.load(f)
            self._validate_schema(level)
        else:
            self._load_all()

    def get_version(self) -> str:
        """Get application version"""
        return self.get(SettingsLevel.APP, "app.version", "0.0.0")

    def get_app_name(self) -> str:
        """Get application name"""
        return self.get(SettingsLevel.APP, "app.name", "Vidnag")


# Global settings instance
settings = SettingsManager()
