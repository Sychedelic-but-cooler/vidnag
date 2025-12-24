"""
Storage Management Utilities
Handles storage directory creation and permission management
"""

import os
import stat
from pathlib import Path
from typing import List, Tuple


class StorageError(Exception):
    """Custom exception for storage-related errors"""
    pass


def init_storage(
    base_path: str = "storage",
    subdirs: List[str] = None,
    create_mode: int = 0o755,
    fix_permissions: bool = True
) -> Tuple[List[str], List[str]]:
    """
    Initialize storage directories with proper permissions

    Aggressively creates all necessary storage directories and sets
    proper permissions. This runs on every application startup to ensure
    the storage system is properly configured.

    Args:
        base_path: Base storage directory path (default: "storage")
        subdirs: List of subdirectories to create (default: ["videos", "thumbnails", "temp"])
        create_mode: Unix permissions for directories (default: 0o755 = rwxr-xr-x)
        fix_permissions: Whether to fix permissions on existing directories (default: True)

    Returns:
        Tuple of (created_paths: List[str], warnings: List[str])

    Example:
        >>> created, warnings = init_storage("storage", ["videos", "thumbnails", "temp"])
        >>> print(f"Created: {len(created)} directories")
    """
    if subdirs is None:
        subdirs = ["videos", "thumbnails", "temp"]

    # Convert to absolute path if relative
    base_path_obj = Path(base_path)
    if not base_path_obj.is_absolute():
        # Make relative to project root (parent of backend/)
        project_root = Path(__file__).parent.parent.parent
        base_path_obj = project_root / base_path

    directories_to_create = [base_path_obj]
    directories_to_create.extend([base_path_obj / subdir for subdir in subdirs])

    created = []
    warnings = []

    for directory in directories_to_create:
        dir_path = str(directory)

        try:
            # Create directory if it doesn't exist
            if not directory.exists():
                directory.mkdir(parents=True, mode=create_mode, exist_ok=True)
                created.append(dir_path)

                # Verify it was created
                if not directory.exists():
                    warnings.append(f"Directory creation reported success but path doesn't exist: {dir_path}")
                    continue

            # Fix permissions on existing directories if requested
            if fix_permissions:
                try:
                    current_mode = directory.stat().st_mode
                    current_perms = stat.S_IMODE(current_mode)

                    if current_perms != create_mode:
                        directory.chmod(create_mode)
                        # Verify permission change
                        new_mode = directory.stat().st_mode
                        if stat.S_IMODE(new_mode) != create_mode:
                            warnings.append(
                                f"Failed to set permissions on {dir_path}: "
                                f"wanted {oct(create_mode)}, got {oct(stat.S_IMODE(new_mode))}"
                            )
                except (OSError, PermissionError) as e:
                    warnings.append(f"Could not set permissions on {dir_path}: {e}")

            # Final writability check
            if not os.access(directory, os.W_OK):
                warnings.append(f"Directory exists but is not writable: {dir_path}")
            else:
                # Create .gitkeep file to preserve empty directories in git
                gitkeep = directory / ".gitkeep"
                if not gitkeep.exists():
                    try:
                        gitkeep.touch()
                    except Exception as e:
                        warnings.append(f"Could not create .gitkeep in {dir_path}: {e}")

        except PermissionError as e:
            warnings.append(f"Permission denied creating {dir_path}: {e}")
        except OSError as e:
            warnings.append(f"OS error creating {dir_path}: {e}")
        except Exception as e:
            warnings.append(f"Unexpected error with {dir_path}: {e}")

    return created, warnings


def get_storage_info(base_path: str = "storage") -> dict:
    """
    Get information about storage directories

    Args:
        base_path: Base storage directory path

    Returns:
        Dictionary with storage information including size, permissions, etc.

    Example:
        >>> info = get_storage_info("storage")
        >>> print(info["total_size_mb"])
    """
    base_path_obj = Path(base_path)
    if not base_path_obj.is_absolute():
        project_root = Path(__file__).parent.parent.parent
        base_path_obj = project_root / base_path

    info = {
        "base_path": str(base_path_obj),
        "exists": base_path_obj.exists(),
        "writable": os.access(base_path_obj, os.W_OK) if base_path_obj.exists() else False,
        "subdirs": {}
    }

    if base_path_obj.exists():
        # Get size of all files
        total_size = 0
        for subdir in ["videos", "thumbnails", "temp"]:
            subdir_path = base_path_obj / subdir
            if subdir_path.exists():
                size = sum(f.stat().st_size for f in subdir_path.rglob('*') if f.is_file())
                info["subdirs"][subdir] = {
                    "exists": True,
                    "writable": os.access(subdir_path, os.W_OK),
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 2)
                }
                total_size += size
            else:
                info["subdirs"][subdir] = {"exists": False}

        info["total_size_bytes"] = total_size
        info["total_size_mb"] = round(total_size / (1024 * 1024), 2)
        info["total_size_gb"] = round(total_size / (1024 * 1024 * 1024), 2)

    return info


def verify_storage_writable(base_path: str = "storage") -> Tuple[bool, List[str]]:
    """
    Verify that all storage directories are writable

    Args:
        base_path: Base storage directory path

    Returns:
        Tuple of (all_writable: bool, errors: List[str])

    Example:
        >>> writable, errors = verify_storage_writable("storage")
        >>> if not writable:
        ...     print("Storage errors:", errors)
    """
    base_path_obj = Path(base_path)
    if not base_path_obj.is_absolute():
        project_root = Path(__file__).parent.parent.parent
        base_path_obj = project_root / base_path

    errors = []

    # Check base directory
    if not base_path_obj.exists():
        errors.append(f"Base storage directory does not exist: {base_path_obj}")
    elif not os.access(base_path_obj, os.W_OK):
        errors.append(f"Base storage directory not writable: {base_path_obj}")

    # Check subdirectories
    for subdir in ["videos", "thumbnails", "temp"]:
        subdir_path = base_path_obj / subdir
        if not subdir_path.exists():
            errors.append(f"Subdirectory does not exist: {subdir_path}")
        elif not os.access(subdir_path, os.W_OK):
            errors.append(f"Subdirectory not writable: {subdir_path}")

    return len(errors) == 0, errors
