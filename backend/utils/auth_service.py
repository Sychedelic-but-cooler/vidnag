"""
Authentication Service
Handles all auth logic: login, registration, session management
ALL auth checks happen server-side
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from backend.models import User, Session as DBSession
from backend.utils.password import hash_password, verify_password, check_password_requirements
from backend.utils.jwt import JWTManager


class AuthError(Exception):
    """Base exception for authentication errors"""
    pass


class LoginFailedError(AuthError):
    """Login failed - generic error to prevent information leakage"""
    pass


class AccountLockedError(AuthError):
    """Account is locked"""
    pass


class RegistrationError(AuthError):
    """Registration failed"""
    pass


class AuthService:
    """
    Authentication service - all auth logic happens here on server side

    NO sensitive information is sent to client:
    - Don't tell client if username exists
    - Don't tell client if password is wrong vs account locked
    - Don't tell client specific lockout reasons
    - Generic "login failed" errors only
    """

    def __init__(self, jwt_manager: JWTManager, settings_manager):
        self.jwt = jwt_manager
        self.settings = settings_manager

    def register_user(
        self,
        db: Session,
        username: str,
        email: str,
        password: str,
        is_admin: bool = False
    ) -> Tuple[User, str, str]:
        """
        Register a new user

        Args:
            db: Database session
            username: Username
            email: Email address
            password: Plain text password
            is_admin: Whether user is admin (only for first user or admin creation)

        Returns:
            Tuple of (User, access_token, refresh_token)

        Raises:
            RegistrationError: If registration fails
        """
        from backend.core.settings import SettingsLevel

        # Check if registration is enabled
        registration_enabled = self.settings.get(
            SettingsLevel.ADMIN,
            "users.registration_enabled",
            True
        )

        if not registration_enabled:
            raise RegistrationError("Registration is currently disabled")

        # Check if admin registration is allowed
        if is_admin:
            allow_admin_registration = self.settings.get(
                SettingsLevel.ADMIN,
                "users.allow_admin_registration",
                False
            )
            if not allow_admin_registration:
                raise RegistrationError("Admin registration is not allowed")

        # Validate username
        if len(username) < 3 or len(username) > 50:
            raise RegistrationError("Username must be between 3 and 50 characters")

        # Check if username exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise RegistrationError("Username already taken")

        # Check if email exists
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise RegistrationError("Email already registered")

        # Validate password
        min_length = self.settings.get(SettingsLevel.ADMIN, "users.password_min_length", 8)
        require_uppercase = self.settings.get(SettingsLevel.ADMIN, "users.password_require_uppercase", False)
        require_lowercase = self.settings.get(SettingsLevel.ADMIN, "users.password_require_lowercase", False)
        require_numbers = self.settings.get(SettingsLevel.ADMIN, "users.password_require_numbers", False)
        require_special = self.settings.get(SettingsLevel.ADMIN, "users.password_require_special", False)

        is_valid, error = check_password_requirements(
            password,
            min_length,
            require_uppercase,
            require_lowercase,
            require_numbers,
            require_special
        )

        if not is_valid:
            raise RegistrationError(error)

        # Hash password
        password_hash = hash_password(password)

        # Get default storage quota
        default_quota = self.settings.get(
            SettingsLevel.ADMIN,
            "users.default_storage_quota_gb",
            10
        ) * 1024 * 1024 * 1024  # Convert to bytes

        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            is_admin=is_admin,
            storage_quota=default_quota,
            storage_used=0
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # Generate tokens
        access_token = self.jwt.create_access_token(
            user_id=user.id,
            is_admin=user.is_admin,
            expires_delta=self._get_token_expiry()
        )

        refresh_token = self.jwt.create_refresh_token(user_id=user.id)

        return user, access_token, refresh_token

    def login(
        self,
        db: Session,
        username: str,
        password: str,
        ip_address: str,
        user_agent: Optional[str] = None
    ) -> Tuple[User, str, str]:
        """
        Authenticate user and create session

        Args:
            db: Database session
            username: Username or email
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Tuple of (User, access_token, refresh_token)

        Raises:
            LoginFailedError: Generic login failed (don't leak info!)
            AccountLockedError: Account is locked
        """
        # Try to find user by username or email
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()

        # SECURITY: Don't tell client if user exists
        if not user:
            raise LoginFailedError("Invalid credentials")

        # Check if account is active
        if not user.is_active:
            # SECURITY: Don't tell client account is inactive - generic error
            raise LoginFailedError("Invalid credentials")

        # Verify password
        if not verify_password(password, user.password_hash):
            # Password wrong - could implement lockout here
            raise LoginFailedError("Invalid credentials")

        # Update last login
        user.last_login = datetime.utcnow()
        user.last_ip = ip_address
        user.login_count += 1

        # Generate tokens
        access_token = self.jwt.create_access_token(
            user_id=user.id,
            is_admin=user.is_admin,
            expires_delta=self._get_token_expiry()
        )

        refresh_token = self.jwt.create_refresh_token(user_id=user.id)

        # Create session record
        session = DBSession(
            user_id=user.id,
            token_hash=self.jwt.get_token_hash(access_token),
            refresh_token_hash=self.jwt.get_token_hash(refresh_token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + self._get_token_expiry()
        )

        db.add(session)
        db.commit()

        return user, access_token, refresh_token

    def verify_token(self, db: Session, token: str) -> Optional[User]:
        """
        Verify JWT token and return user

        ALL checks happen server-side:
        - Token signature
        - Token expiry
        - Session validity
        - User active status
        - Admin status (from token, verified against DB)

        Args:
            db: Database session
            token: JWT access token

        Returns:
            User: User object if valid, None otherwise
        """
        # Decode token
        payload = self.jwt.verify_token(token)
        if not payload:
            return None

        # Verify token type
        if not self.jwt.verify_token_type(payload, "access"):
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        # Check if user is active (server-side check!)
        if not user.is_active:
            return None

        # Verify session exists and is active
        token_hash = self.jwt.get_token_hash(token)
        session = db.query(DBSession).filter(
            DBSession.token_hash == token_hash,
            DBSession.user_id == user_id,
            DBSession.is_active == True
        ).first()

        if not session:
            return None

        # Check session expiry
        if session.is_expired():
            return None

        # Update last activity
        session.last_activity = datetime.utcnow()
        db.commit()

        return user

    def refresh_access_token(
        self,
        db: Session,
        refresh_token: str
    ) -> Optional[Tuple[str, str]]:
        """
        Refresh access token using refresh token

        Args:
            db: Database session
            refresh_token: Refresh token

        Returns:
            Tuple of (new_access_token, new_refresh_token) or None
        """
        # Verify refresh token
        payload = self.jwt.verify_token(refresh_token)
        if not payload:
            return None

        # Verify token type
        if not self.jwt.verify_token_type(payload, "refresh"):
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return None

        # Verify refresh token session
        token_hash = self.jwt.get_token_hash(refresh_token)
        session = db.query(DBSession).filter(
            DBSession.refresh_token_hash == token_hash,
            DBSession.user_id == user_id,
            DBSession.is_active == True
        ).first()

        if not session:
            return None

        # Generate new tokens
        new_access_token = self.jwt.create_access_token(
            user_id=user.id,
            is_admin=user.is_admin,
            expires_delta=self._get_token_expiry()
        )

        new_refresh_token = self.jwt.create_refresh_token(user_id=user.id)

        # Update session
        session.token_hash = self.jwt.get_token_hash(new_access_token)
        session.refresh_token_hash = self.jwt.get_token_hash(new_refresh_token)
        session.expires_at = datetime.utcnow() + self._get_token_expiry()
        session.last_activity = datetime.utcnow()

        db.commit()

        return new_access_token, new_refresh_token

    def logout(self, db: Session, token: str) -> bool:
        """
        Logout user (revoke session)

        Args:
            db: Database session
            token: Access token

        Returns:
            bool: True if session was revoked
        """
        token_hash = self.jwt.get_token_hash(token)

        session = db.query(DBSession).filter(
            DBSession.token_hash == token_hash,
            DBSession.is_active == True
        ).first()

        if session:
            session.revoke("user_logout")
            db.commit()
            return True

        return False

    def logout_all_sessions(self, db: Session, user_id: int) -> int:
        """
        Logout all user sessions (revoke all)

        Args:
            db: Database session
            user_id: User ID

        Returns:
            int: Number of sessions revoked
        """
        sessions = db.query(DBSession).filter(
            DBSession.user_id == user_id,
            DBSession.is_active == True
        ).all()

        count = 0
        for session in sessions:
            session.revoke("user_logout_all")
            count += 1

        db.commit()
        return count

    def _get_token_expiry(self) -> timedelta:
        """Get token expiry from settings"""
        from backend.core.settings import SettingsLevel

        days = self.settings.get(
            SettingsLevel.APP,
            "security.session_timeout_days",
            7
        )
        return timedelta(days=days)
