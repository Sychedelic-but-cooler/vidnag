"""
File Operations Utilities
Provides safe file operations, UUID generation, and checksums
"""

import uuid
import hashlib
import shutil
import os
from pathlib import Path
from typing import Optional


class FileOperationError(Exception):
    """Custom exception for file operation errors"""
    pass


def generate_video_uuid(extension: str = "mp4") -> str:
    """
    Generate a unique filename using UUID4

    Args:
        extension: File extension (without dot), defaults to "mp4"

    Returns:
        Filename in format: a7b3c9d2-1234-5678-abcd-ef1234567890.mp4

    Example:
        >>> filename = generate_video_uuid("webm")
        >>> # Returns something like: "3f8a9b2c-4e7f-4a1b-9c3d-8f2e5b6a7c9d.webm"
    """
    # Generate UUID4 (random UUID)
    file_uuid = uuid.uuid4()

    # Ensure extension doesn't have leading dot
    extension = extension.lstrip('.')

    return f"{file_uuid}.{extension}"


def calculate_file_checksum(file_path: str, algorithm: str = "sha256") -> str:
    """
    Calculate checksum of a file using specified algorithm

    Reads file in chunks to handle large files efficiently without
    loading entire file into memory.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm ('sha256', 'md5', 'sha1'), defaults to 'sha256'

    Returns:
        Hexadecimal string of the checksum

    Raises:
        FileOperationError: If file doesn't exist or can't be read
        ValueError: If algorithm is not supported

    Example:
        >>> checksum = calculate_file_checksum("/path/to/video.mp4")
        >>> # Returns: "a7b3c9d2..."
    """
    # Validate algorithm
    supported_algorithms = {'sha256', 'md5', 'sha1', 'sha512'}
    if algorithm not in supported_algorithms:
        raise ValueError(
            f"Unsupported algorithm '{algorithm}'. "
            f"Supported: {', '.join(supported_algorithms)}"
        )

    # Check if file exists
    if not os.path.exists(file_path):
        raise FileOperationError(f"File not found: {file_path}")

    if not os.path.isfile(file_path):
        raise FileOperationError(f"Path is not a file: {file_path}")

    # Create hash object
    try:
        hash_obj = hashlib.new(algorithm)
    except ValueError as e:
        raise ValueError(f"Invalid hash algorithm: {e}")

    # Read and hash file in chunks (8KB chunks)
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_obj.update(chunk)
    except IOError as e:
        raise FileOperationError(f"Failed to read file: {e}")

    return hash_obj.hexdigest()


def safe_move_file(
    src: str,
    dest_dir: str,
    filename: str,
    storage_root: str = "storage"
) -> str:
    """
    Move file with security checks to prevent path traversal attacks

    Security measures:
    1. Resolve absolute paths to prevent symlink attacks
    2. Verify destination is within storage_root
    3. Sanitize filename to remove path components
    4. Create directories if needed
    5. Move file atomically

    Args:
        src: Source file path
        dest_dir: Destination directory (must be within storage_root)
        filename: Destination filename (will be sanitized)
        storage_root: Root directory for storage (default: storage)

    Returns:
        Absolute path to the moved file

    Raises:
        FileOperationError: If operation fails or security check fails

    Example:
        >>> moved_path = safe_move_file(
        ...     "/tmp/download.mp4",
        ...     "storage/videos",
        ...     "a7b3c9d2-1234-5678-abcd-ef1234567890.mp4"
        ... )
    """
    # Check source file exists
    if not os.path.exists(src):
        raise FileOperationError(f"Source file not found: {src}")

    if not os.path.isfile(src):
        raise FileOperationError(f"Source is not a file: {src}")

    # Resolve absolute paths (prevents symlink attacks)
    try:
        src_path = Path(src).resolve()
        dest_dir_path = Path(dest_dir).resolve()
        storage_root_path = Path(storage_root).resolve()
    except Exception as e:
        raise FileOperationError(f"Failed to resolve paths: {e}")

    # Security check: Ensure destination is within storage root
    try:
        dest_dir_path.relative_to(storage_root_path)
    except ValueError:
        raise FileOperationError(
            f"Destination directory '{dest_dir}' is outside storage root '{storage_root}'"
        )

    # Sanitize filename (remove any path components)
    safe_filename = Path(filename).name
    if not safe_filename or safe_filename in ('.', '..'):
        raise FileOperationError(f"Invalid filename: {filename}")

    # Build destination path
    dest_path = dest_dir_path / safe_filename

    # Check if destination already exists
    if dest_path.exists():
        raise FileOperationError(f"Destination file already exists: {dest_path}")

    # Create destination directory if it doesn't exist
    try:
        dest_dir_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise FileOperationError(f"Failed to create destination directory: {e}")

    # Move file atomically
    try:
        shutil.move(str(src_path), str(dest_path))
    except Exception as e:
        raise FileOperationError(f"Failed to move file: {e}")

    return str(dest_path)


def get_file_size(file_path: str) -> int:
    """
    Get size of a file in bytes

    Args:
        file_path: Path to the file

    Returns:
        File size in bytes

    Raises:
        FileOperationError: If file doesn't exist or can't be accessed
    """
    try:
        return os.path.getsize(file_path)
    except OSError as e:
        raise FileOperationError(f"Failed to get file size: {e}")


def safe_delete_file(file_path: str, storage_root: str = "/var/vidnag/storage") -> bool:
    """
    Safely delete a file with security checks

    Args:
        file_path: Path to file to delete
        storage_root: Root directory for storage (default: /var/vidnag/storage)

    Returns:
        True if file was deleted, False if file didn't exist

    Raises:
        FileOperationError: If deletion fails or security check fails
    """
    # Check if file exists
    if not os.path.exists(file_path):
        return False

    # Resolve absolute path
    try:
        file_path_resolved = Path(file_path).resolve()
        storage_root_path = Path(storage_root).resolve()
    except Exception as e:
        raise FileOperationError(f"Failed to resolve paths: {e}")

    # Security check: Ensure file is within storage root
    try:
        file_path_resolved.relative_to(storage_root_path)
    except ValueError:
        raise FileOperationError(
            f"File '{file_path}' is outside storage root '{storage_root}'"
        )

    # Delete file
    try:
        os.remove(file_path_resolved)
        return True
    except OSError as e:
        raise FileOperationError(f"Failed to delete file: {e}")


def create_directory(dir_path: str, storage_root: str = "/var/vidnag/storage") -> None:
    """
    Create a directory with security checks

    Args:
        dir_path: Path to directory to create
        storage_root: Root directory for storage (default: /var/vidnag/storage)

    Raises:
        FileOperationError: If creation fails or security check fails
    """
    # Resolve absolute path
    try:
        dir_path_resolved = Path(dir_path).resolve()
        storage_root_path = Path(storage_root).resolve()
    except Exception as e:
        raise FileOperationError(f"Failed to resolve paths: {e}")

    # Security check: Ensure directory is within storage root
    try:
        dir_path_resolved.relative_to(storage_root_path)
    except ValueError:
        raise FileOperationError(
            f"Directory '{dir_path}' is outside storage root '{storage_root}'"
        )

    # Create directory
    try:
        dir_path_resolved.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise FileOperationError(f"Failed to create directory: {e}")
