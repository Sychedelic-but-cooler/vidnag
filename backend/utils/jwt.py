"""
JWT Token Management
Handles JWT token generation and validation
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError


class JWTManager:
    """Manages JWT token creation and validation"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_access_token(
        self,
        user_id: int,
        is_admin: bool = False,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token

        Args:
            user_id: User ID
            is_admin: Whether user is admin
            expires_delta: Token expiration time (default: from settings)

        Returns:
            str: JWT token
        """
        if expires_delta is None:
            expires_delta = timedelta(days=7)  # Default from settings

        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": str(user_id),  # Subject (user ID)
            "user_id": user_id,
            "is_admin": is_admin,
            "exp": expire,  # Expiration time
            "iat": datetime.utcnow(),  # Issued at
            "type": "access"
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def create_refresh_token(
        self,
        user_id: int,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT refresh token (longer lived)

        Args:
            user_id: User ID
            expires_delta: Token expiration time (default: 30 days)

        Returns:
            str: JWT refresh token
        """
        if expires_delta is None:
            expires_delta = timedelta(days=30)

        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": str(user_id),
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token

        Args:
            token: JWT token string

        Returns:
            dict: Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload

        except ExpiredSignatureError:
            # Token expired
            return None

        except JWTError:
            # Invalid token
            return None

    def get_token_hash(self, token: str) -> str:
        """
        Get SHA256 hash of token for database storage

        We store token hashes in the database, not the actual tokens.
        This prevents token leakage if database is compromised.

        Args:
            token: JWT token string

        Returns:
            str: SHA256 hash of token
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def verify_token_type(self, payload: Dict[str, Any], expected_type: str) -> bool:
        """
        Verify token is of expected type (access or refresh)

        Args:
            payload: Decoded JWT payload
            expected_type: Expected token type ('access' or 'refresh')

        Returns:
            bool: True if token type matches
        """
        return payload.get("type") == expected_type

    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """
        Extract user ID from token without full validation

        Args:
            token: JWT token string

        Returns:
            int: User ID if token is valid, None otherwise
        """
        payload = self.verify_token(token)
        if payload:
            return payload.get("user_id")
        return None

    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired without full validation

        Args:
            token: JWT token string

        Returns:
            bool: True if expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Don't raise on expiry
            )
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp) < datetime.utcnow()
            return True

        except JWTError:
            return True
