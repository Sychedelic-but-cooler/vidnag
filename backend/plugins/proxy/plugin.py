"""
Proxy Plugin
Configures IP extraction from reverse proxy headers
"""

from typing import Dict, Any
from backend.plugins.base import Plugin


class ProxyPlugin(Plugin):
    """
    Proxy configuration plugin

    This plugin doesn't provide middleware itself - IP extraction is always
    active in the core. This plugin just provides configuration for which
    proxies to trust and which headers to check.

    The core IP extraction reads this plugin's config.
    """

    @property
    def name(self) -> str:
        return "proxy"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Configures trusted proxies and headers for IP extraction"

    def validate_config(self) -> None:
        """Validate proxy configuration"""
        if not isinstance(self.config.get('trusted_proxies', []), list):
            raise ValueError("trusted_proxies must be a list")

        if not isinstance(self.config.get('headers', []), list):
            raise ValueError("headers must be a list")

        # Validate that we have at least one header
        headers = self.config.get('headers', [])
        if not headers:
            raise ValueError("At least one proxy header must be specified")

    def on_startup(self) -> None:
        """Log proxy configuration on startup"""
        trusted_proxies = self.config.get('trusted_proxies', [])
        headers = self.config.get('headers', [])

        self.log_info(
            f"Proxy plugin configured: {len(trusted_proxies)} trusted proxies, "
            f"checking headers: {', '.join(headers)}"
        )

        if not trusted_proxies:
            self.log_warning(
                "No trusted proxies configured - will use direct connection IP. "
                "If behind a reverse proxy, configure trusted_proxies in admin settings."
            )


# Required export
PluginClass = ProxyPlugin
