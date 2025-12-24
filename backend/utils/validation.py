"""
URL and Input Validation Utilities
Provides validation for URLs, filenames, and other user inputs
"""

from typing import Tuple, Optional, List
from urllib.parse import urlparse
import re


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class URLValidator:
    """Validates URLs for video downloads"""

    def __init__(self, settings_manager):
        """
        Initialize URL validator

        Args:
            settings_manager: Settings manager instance for accessing domain whitelists
        """
        self.settings = settings_manager

    def validate(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a URL for download

        Checks:
        1. Valid URL format
        2. Scheme is http or https
        3. Domain in allowed_domains list
        4. Not in blocked_domains list
        5. Length < 1024 chars
        6. No malicious patterns (javascript:, file:, data:)

        Args:
            url: The URL to validate

        Returns:
            Tuple of (is_valid, error_message)
            If valid: (True, None)
            If invalid: (False, "Error description")
        """
        # Check length
        if not url or len(url) > 1024:
            return False, "URL must be between 1 and 1024 characters"

        # Check for malicious patterns
        url_lower = url.lower()
        malicious_schemes = ['javascript:', 'file:', 'data:', 'vbscript:', 'about:']
        for scheme in malicious_schemes:
            if url_lower.startswith(scheme):
                return False, f"URL scheme '{scheme}' is not allowed"

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"

        # Check scheme
        if parsed.scheme not in ('http', 'https'):
            return False, "Only HTTP and HTTPS URLs are allowed"

        # Check if domain is present
        if not parsed.netloc:
            return False, "URL must have a domain"

        # Get domain whitelist and blacklist from settings
        try:
            from backend.core.settings import SettingsLevel
            allowed_domains = self.settings.get(
                SettingsLevel.ADMIN,
                "downloads.allowed_domains",
                []
            )
            blocked_domains = self.settings.get(
                SettingsLevel.ADMIN,
                "downloads.blocked_domains",
                []
            )
        except Exception as e:
            return False, f"Failed to load domain settings: {str(e)}"

        # Check blocked domains first
        domain = parsed.netloc.lower()
        if self._is_domain_in_list(domain, blocked_domains):
            return False, f"Domain {domain} is blocked"

        # Check allowed domains
        if not self._is_domain_in_list(domain, allowed_domains):
            return False, f"Domain {domain} is not in the allowed list"

        return True, None

    def _is_domain_in_list(self, domain: str, domain_list: List[str]) -> bool:
        """
        Check if domain matches any entry in the domain list
        Supports exact matches and subdomain wildcard matching

        Args:
            domain: The domain to check (e.g., "www.youtube.com")
            domain_list: List of allowed/blocked domains (e.g., ["youtube.com"])

        Returns:
            True if domain matches, False otherwise
        """
        # Remove port if present
        domain = domain.split(':')[0].lower()

        for allowed in domain_list:
            allowed = allowed.lower()

            # Exact match
            if domain == allowed:
                return True

            # Subdomain match (e.g., www.youtube.com matches youtube.com)
            if domain.endswith('.' + allowed):
                return True

        return False


class FilenameValidator:
    """Validates and sanitizes filenames"""

    # Characters not allowed in filenames across most filesystems
    INVALID_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

    # Reserved Windows filenames
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }

    @classmethod
    def sanitize(cls, filename: str, replacement: str = '_') -> str:
        """
        Sanitize a filename by removing or replacing invalid characters

        Args:
            filename: The filename to sanitize
            replacement: Character to replace invalid chars with (default: '_')

        Returns:
            Sanitized filename safe for most filesystems
        """
        if not filename:
            return 'unnamed'

        # Remove any path components (security)
        filename = filename.split('/')[-1].split('\\')[-1]

        # Replace invalid characters
        filename = re.sub(cls.INVALID_CHARS, replacement, filename)

        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')

        # Check for reserved names (Windows)
        name_without_ext = filename.rsplit('.', 1)[0].upper()
        if name_without_ext in cls.RESERVED_NAMES:
            filename = f"{replacement}{filename}"

        # Limit length (most filesystems support 255, we'll use 200 to be safe)
        if len(filename) > 200:
            # Try to preserve extension
            if '.' in filename:
                name, ext = filename.rsplit('.', 1)
                max_name_len = 200 - len(ext) - 1
                filename = f"{name[:max_name_len]}.{ext}"
            else:
                filename = filename[:200]

        # If we ended up with empty string, use default
        if not filename:
            return 'unnamed'

        return filename

    @classmethod
    def validate(cls, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a filename

        Args:
            filename: The filename to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not filename:
            return False, "Filename cannot be empty"

        # Check for path traversal attempts
        if '/' in filename or '\\' in filename:
            return False, "Filename cannot contain path separators"

        # Check for invalid characters
        if re.search(cls.INVALID_CHARS, filename):
            return False, "Filename contains invalid characters"

        # Check length
        if len(filename) > 255:
            return False, "Filename is too long (max 255 characters)"

        # Check for reserved names
        name_without_ext = filename.rsplit('.', 1)[0].upper()
        if name_without_ext in cls.RESERVED_NAMES:
            return False, f"Filename uses reserved name: {name_without_ext}"

        return True, None
