"""
Password Hashing Utilities
Secure password hashing using bcrypt
"""

import bcrypt


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        str: Hashed password (base64 encoded)

    Note:
        Bcrypt has a maximum password length of 72 bytes.
        Passwords are automatically truncated to this limit.
    """
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Truncate to 72 bytes, being careful not to split UTF-8 sequences
        password_bytes = password_bytes[:72]
        # Find the last valid UTF-8 character boundary
        while len(password_bytes) > 0:
            try:
                password_bytes.decode('utf-8')
                break
            except UnicodeDecodeError:
                # We cut in the middle of a multi-byte character, try one byte less
                password_bytes = password_bytes[:-1]

    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as string (bcrypt returns bytes)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        bool: True if password matches

    Note:
        Applies the same 72-byte truncation as hash_password for consistency.
    """
    # Apply same 72-byte truncation as when hashing
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        # Find the last valid UTF-8 character boundary
        while len(password_bytes) > 0:
            try:
                password_bytes.decode('utf-8')
                break
            except UnicodeDecodeError:
                password_bytes = password_bytes[:-1]

    # Convert hashed password string back to bytes
    hashed_bytes = hashed_password.encode('utf-8')

    # Verify using bcrypt
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def validate_password_strength(password: str, min_length: int = 8) -> tuple[bool, str]:
    """
    Validate password meets minimum requirements

    Args:
        password: Password to validate
        min_length: Minimum password length

    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"

    # Check for at least one letter and one number (basic requirement)
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)

    if not (has_letter and has_number):
        return False, "Password must contain at least one letter and one number"

    return True, ""


def check_password_requirements(
    password: str,
    min_length: int = 8,
    require_uppercase: bool = False,
    require_lowercase: bool = False,
    require_numbers: bool = False,
    require_special: bool = False
) -> tuple[bool, str]:
    """
    Check password against configurable requirements

    Args:
        password: Password to check
        min_length: Minimum password length
        require_uppercase: Require at least one uppercase letter
        require_lowercase: Require at least one lowercase letter
        require_numbers: Require at least one number
        require_special: Require at least one special character

    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"

    # Warn if password exceeds bcrypt's 72-byte limit (will be truncated)
    if len(password.encode('utf-8')) > 72:
        return False, "Password is too long (maximum 72 bytes)"

    if require_uppercase and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if require_lowercase and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if require_numbers and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"

    if require_special:
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"

    return True, ""
