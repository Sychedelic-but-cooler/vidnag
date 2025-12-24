"""
yt-dlp Wrapper Utilities
Provides subprocess wrapper for yt-dlp operations
"""

import sys
import subprocess
import json
from typing import Dict, List, Optional, Any


class YtDlpError(Exception):
    """Custom exception for yt-dlp errors"""
    pass


class YtDlpWrapper:
    """Wrapper for yt-dlp subprocess operations"""

    @staticmethod
    def get_video_info(url: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Get video metadata without downloading

        Uses yt-dlp's --dump-json flag to extract video information including
        title, duration, filesize estimates, available formats, etc.

        Args:
            url: Video URL to query
            timeout: Timeout in seconds (default: 30)

        Returns:
            Dictionary containing video metadata with keys like:
            - title: Video title
            - duration: Duration in seconds
            - filesize: Estimated size in bytes (may be None)
            - ext: File extension
            - format_id: Format identifier
            - formats: List of available formats
            - thumbnail: URL to thumbnail
            - description: Video description
            - uploader: Channel/uploader name

        Raises:
            YtDlpError: If yt-dlp command fails or returns invalid data
            subprocess.TimeoutExpired: If operation exceeds timeout
        """
        cmd = [
            sys.executable, '-m', 'yt_dlp',
            '--dump-json',
            '--no-playlist',
            url
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )
        except subprocess.TimeoutExpired:
            raise YtDlpError(f"Video info extraction timed out after {timeout} seconds")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else "Unknown error"
            raise YtDlpError(f"Failed to extract video info: {error_msg}")
        except Exception as e:
            raise YtDlpError(f"Unexpected error extracting video info: {str(e)}")

        # Parse JSON output
        try:
            info = json.loads(result.stdout)
            return info
        except json.JSONDecodeError as e:
            raise YtDlpError(f"Failed to parse video info JSON: {str(e)}")

    @staticmethod
    def build_format_selector(max_size_mb: int) -> str:
        """
        Build format selector string for yt-dlp

        Uses a robust fallback strategy that tries multiple format options.
        Size limiting is handled by --max-filesize flag during download,
        not by pre-filtering formats (which often fails due to missing metadata).

        Strategy:
        1. Try best video + best audio (YouTube's typical separate streams)
        2. Fall back to best combined format
        3. Fall back to best video only
        4. Fall back to best available format

        Args:
            max_size_mb: Maximum file size in megabytes (used for reference)

        Returns:
            Format selector string for yt-dlp

        Example:
            "bestvideo+bestaudio/best"
        """
        # Don't pre-filter by filesize in format selector - let --max-filesize handle it
        # This prevents "format not available" errors when filesize metadata is missing
        return "bestvideo+bestaudio/best"

    @staticmethod
    def build_download_command(
        url: str,
        output_path: str,
        max_size_mb: int = 1000,
        merge_format: str = "mp4"
    ) -> List[str]:
        """
        Build yt-dlp download command

        Args:
            url: Video URL to download
            output_path: Output file path template (use %(ext)s for auto extension)
            max_size_mb: Maximum file size in megabytes (default: 1000)
            merge_format: Output format for merging streams (default: "mp4")

        Returns:
            List of command arguments ready for subprocess.run()

        Example:
            >>> cmd = build_download_command(
            ...     "https://youtube.com/watch?v=dQw4w9WgXcQ",
            ...     "/tmp/video.%(ext)s",
            ...     max_size_mb=1000
            ... )
            >>> # subprocess.run(cmd)
        """
        format_selector = YtDlpWrapper.build_format_selector(max_size_mb)

        cmd = [
            sys.executable, '-m', 'yt_dlp',
            '--format', format_selector,
            '--merge-output-format', merge_format,
            '--output', output_path,
            '--no-playlist',
            '--progress',
            '--newline',  # Print progress on new lines for easier parsing
            '--max-filesize', f'{max_size_mb}M',
            url
        ]

        return cmd

    @staticmethod
    def parse_progress_line(line: str) -> Optional[Dict[str, Any]]:
        """
        Parse yt-dlp progress output line

        Progress lines follow format:
        [download]  45.2% of 123.45MiB at 1.23MiB/s ETA 00:45

        Args:
            line: Single line of yt-dlp output

        Returns:
            Dictionary with progress info if line contains progress, None otherwise:
            {
                'percent': 45.2,
                'total_size': '123.45MiB',
                'speed': '1.23MiB/s',
                'eta': '00:45'
            }
        """
        line = line.strip()

        # Check if this is a download progress line
        if not line.startswith('[download]'):
            return None

        # Try to parse percentage
        percent_str = None
        if '%' in line:
            parts = line.split('%')
            if len(parts) >= 2:
                # Extract number before %
                before_percent = parts[0].split()[-1]
                try:
                    percent_str = float(before_percent)
                except ValueError:
                    pass

        # Extract other components using keywords
        total_size = None
        speed = None
        eta = None

        if ' of ' in line:
            of_parts = line.split(' of ', 1)
            if len(of_parts) == 2:
                size_parts = of_parts[1].split(' at ', 1)
                total_size = size_parts[0].strip()

                if len(size_parts) == 2:
                    speed_parts = size_parts[1].split(' ETA ', 1)
                    speed = speed_parts[0].strip()

                    if len(speed_parts) == 2:
                        eta = speed_parts[1].strip()

        if percent_str is not None:
            return {
                'percent': percent_str,
                'total_size': total_size,
                'speed': speed,
                'eta': eta
            }

        return None

    @staticmethod
    def check_availability() -> bool:
        """
        Check if yt-dlp is available and functioning

        Returns:
            True if yt-dlp is available, False otherwise
        """
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'yt_dlp', '--version'],
                capture_output=True,
                text=True,
                timeout=5,
                check=True
            )
            # If we get here, yt-dlp is available
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def get_version() -> Optional[str]:
        """
        Get yt-dlp version

        Returns:
            Version string or None if unavailable
        """
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'yt_dlp', '--version'],
                capture_output=True,
                text=True,
                timeout=5,
                check=True
            )
            return result.stdout.strip()
        except Exception:
            return None
