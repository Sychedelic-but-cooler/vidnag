"""
Vidnag Plugin Manager
Manages plugin lifecycle and dependencies
"""

import importlib
from typing import Dict, List, Type, Optional
from pathlib import Path
from fastapi import FastAPI

from backend.plugins.base import Plugin


class PluginManager:
    """Manages plugin lifecycle and dependencies"""

    def __init__(self, settings_manager, logger):
        self.settings = settings_manager
        self.logger = logger
        self.plugins: Dict[str, Plugin] = {}
        self.load_order: List[str] = []

    def discover_plugins(self) -> None:
        """Auto-discover plugins in plugins/ directory"""
        from backend.core.settings import SettingsLevel

        enabled = self.settings.get(SettingsLevel.ADMIN, "plugins.enabled", [])
        load_order = self.settings.get(SettingsLevel.ADMIN, "plugins.load_order", [])
        disabled = self.settings.get(SettingsLevel.ADMIN, "plugins.disabled", [])

        self.logger.app.info(
            f"Discovering plugins: enabled={enabled}, disabled={disabled}"
        )

        # Load plugins in specified order
        for plugin_name in load_order:
            if plugin_name in enabled and plugin_name not in disabled:
                try:
                    self._load_plugin(plugin_name)
                except Exception as e:
                    self.logger.app.error(
                        f"Failed to load plugin '{plugin_name}': {e}",
                        error=str(e)
                    )

        # Load any enabled plugins not in load_order
        for plugin_name in enabled:
            if plugin_name not in disabled and plugin_name not in self.plugins:
                try:
                    self._load_plugin(plugin_name)
                except Exception as e:
                    self.logger.app.error(
                        f"Failed to load plugin '{plugin_name}': {e}",
                        error=str(e)
                    )

        self.logger.app.info(f"Loaded {len(self.plugins)} plugins: {list(self.plugins.keys())}")

    def _load_plugin(self, plugin_name: str) -> None:
        """Load a single plugin"""
        try:
            # Import plugin module
            module = importlib.import_module(f"backend.plugins.{plugin_name}.plugin")

            # Get plugin class
            plugin_class = getattr(module, 'PluginClass', None)
            if not plugin_class:
                raise ImportError(f"Plugin {plugin_name} does not export 'PluginClass'")

            # Get plugin config
            config = self.settings.get_plugin_config(plugin_name)

            # Instantiate plugin
            plugin = plugin_class(config)

            # Set logger
            plugin.set_logger(self.logger)

            # Validate config
            plugin.validate_config()

            # Check dependencies
            self._check_dependencies(plugin)

            # Store plugin
            self.plugins[plugin_name] = plugin
            self.load_order.append(plugin_name)

            self.logger.app.info(
                f"Loaded plugin: {plugin.name} v{plugin.version}",
                plugin=plugin.name,
                version=plugin.version
            )

        except Exception as e:
            self.logger.app.error(
                f"Failed to load plugin {plugin_name}: {e}",
                plugin=plugin_name,
                error=str(e)
            )
            raise

    def _check_dependencies(self, plugin: Plugin) -> None:
        """Check if plugin dependencies are loaded"""
        for dep in plugin.dependencies:
            if dep not in self.plugins:
                raise RuntimeError(
                    f"Plugin '{plugin.name}' requires '{dep}' but it is not loaded"
                )

    def initialize_plugins(self, app: FastAPI) -> None:
        """Initialize all enabled plugins"""
        self.logger.app.info("Initializing plugins...")

        # Initialize in load order
        for plugin_name in self.load_order:
            plugin = self.plugins[plugin_name]
            try:
                self.logger.app.info(f"Initializing plugin: {plugin.name}")
                plugin.initialize(app)

                # Register routes
                plugin.register_routes(app)

                # Add middleware (in reverse order so first plugin wraps outermost)
                middleware = plugin.get_middleware()
                if middleware:
                    app.add_middleware(middleware(app))
                    self.logger.app.info(f"Added middleware for: {plugin.name}")

            except Exception as e:
                self.logger.app.error(
                    f"Failed to initialize plugin '{plugin.name}': {e}",
                    plugin=plugin.name,
                    error=str(e)
                )
                raise

        self.logger.app.info(f"Initialized {len(self.plugins)} plugins")

    def startup_plugins(self) -> None:
        """Call startup hooks for all plugins"""
        self.logger.app.info("Starting up plugins...")

        for plugin_name in self.load_order:
            plugin = self.plugins[plugin_name]
            try:
                plugin.on_startup()
                self.logger.app.info(f"Started plugin: {plugin.name}")
            except Exception as e:
                self.logger.app.error(
                    f"Plugin '{plugin.name}' startup failed: {e}",
                    plugin=plugin.name,
                    error=str(e)
                )

    def shutdown_plugins(self) -> None:
        """Call shutdown hooks for all plugins"""
        self.logger.app.info("Shutting down plugins...")

        # Shutdown in reverse order
        for plugin_name in reversed(self.load_order):
            plugin = self.plugins[plugin_name]
            try:
                plugin.on_shutdown()
                self.logger.app.info(f"Shutdown plugin: {plugin.name}")
            except Exception as e:
                self.logger.app.error(
                    f"Plugin '{plugin.name}' shutdown failed: {e}",
                    plugin=plugin.name,
                    error=str(e)
                )

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name"""
        return self.plugins.get(name)

    def is_loaded(self, name: str) -> bool:
        """Check if a plugin is loaded"""
        return name in self.plugins

    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names"""
        return list(self.plugins.keys())

    def reload_plugin_config(self, plugin_name: str) -> None:
        """Reload configuration for a specific plugin"""
        if plugin_name not in self.plugins:
            raise ValueError(f"Plugin '{plugin_name}' is not loaded")

        plugin = self.plugins[plugin_name]
        new_config = self.settings.get_plugin_config(plugin_name)

        plugin.config = new_config
        plugin.validate_config()

        self.logger.app.info(
            f"Reloaded config for plugin: {plugin_name}",
            plugin=plugin_name
        )
