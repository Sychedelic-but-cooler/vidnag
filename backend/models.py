"""
Vidnag Database Models
SQLAlchemy ORM models for all database tables
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey,
    BigInteger, Float, JSON, Index, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import secrets


Base = declarative_base()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class User(Base, TimestampMixin):
    """User account model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # User type
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Storage
    storage_used = Column(BigInteger, default=0, nullable=False)  # bytes
    storage_quota = Column(BigInteger, nullable=False)  # bytes

    # Activity tracking
    last_login = Column(DateTime, nullable=True)
    last_ip = Column(String(45), nullable=True)  # IPv6 compatible
    login_count = Column(Integer, default=0, nullable=False)

    # Email verification
    email_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)

    # Relationships
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    # Constraints
    __table_args__ = (
        CheckConstraint('storage_used >= 0', name='check_storage_used_positive'),
        CheckConstraint('storage_quota > 0', name='check_storage_quota_positive'),
        CheckConstraint('login_count >= 0', name='check_login_count_positive'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', is_admin={self.is_admin})>"


class Video(Base, TimestampMixin):
    """Video file model"""
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Basic info
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # File info
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)  # bytes
    checksum = Column(String(64), nullable=True)  # SHA256

    # Video metadata
    duration = Column(Float, nullable=True)  # seconds
    format = Column(String(50), nullable=True)  # mp4, webm, etc.
    codec_video = Column(String(50), nullable=True)  # h264, vp9, etc.
    codec_audio = Column(String(50), nullable=True)  # aac, opus, etc.
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    fps = Column(Float, nullable=True)
    bitrate = Column(Integer, nullable=True)  # bps

    # Thumbnails
    thumbnail_path = Column(String(512), nullable=True)
    thumbnail_count = Column(Integer, default=0, nullable=False)

    # Source tracking
    source_type = Column(String(20), nullable=False)  # 'upload' or 'download'
    source_url = Column(String(1024), nullable=True)  # Original URL if downloaded

    # Sharing
    visibility = Column(String(20), default='private', nullable=False)  # private, unlisted, public
    share_token = Column(String(64), unique=True, nullable=True, index=True)
    share_expires_at = Column(DateTime, nullable=True)
    view_count = Column(Integer, default=0, nullable=False)

    # Processing status
    status = Column(String(20), default='processing', nullable=False)  # processing, ready, error
    error_message = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="videos")
    processing_jobs = relationship("ProcessingJob", back_populates="video", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint("visibility IN ('private', 'unlisted', 'public')", name='check_visibility'),
        CheckConstraint("source_type IN ('upload', 'download')", name='check_source_type'),
        CheckConstraint("status IN ('processing', 'ready', 'error', 'deleted')", name='check_status'),
        CheckConstraint('file_size > 0', name='check_file_size_positive'),
        CheckConstraint('view_count >= 0', name='check_view_count_positive'),
        Index('idx_video_user_status', 'user_id', 'status'),
        Index('idx_video_visibility_status', 'visibility', 'status'),
    )

    def generate_share_token(self, expiry_days: int = 30) -> str:
        """Generate a unique share token"""
        self.share_token = secrets.token_urlsafe(32)
        self.share_expires_at = datetime.utcnow() + timedelta(days=expiry_days)
        return self.share_token

    def is_share_valid(self) -> bool:
        """Check if share token is still valid"""
        if not self.share_token:
            return False
        if self.share_expires_at and datetime.utcnow() > self.share_expires_at:
            return False
        return True

    def __repr__(self):
        return f"<Video(id={self.id}, title='{self.title}', user_id={self.user_id}, status='{self.status}')>"


class ProcessingJob(Base, TimestampMixin):
    """Video processing job model"""
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Job info
    job_type = Column(String(50), nullable=False)  # transcode, thumbnail, download, etc.
    status = Column(String(20), default='pending', nullable=False)  # pending, running, completed, failed, cancelled
    priority = Column(Integer, default=0, nullable=False)

    # Progress tracking
    progress = Column(Float, default=0.0, nullable=False)  # 0.0 to 100.0
    current_step = Column(String(100), nullable=True)

    # Parameters
    input_params = Column(JSON, nullable=True)  # Input parameters for the job
    output_params = Column(JSON, nullable=True)  # Output parameters/results

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    estimated_duration = Column(Integer, nullable=True)  # seconds

    # Error handling
    error_message = Column(Text, nullable=True)
    error_trace = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # Worker info
    worker_id = Column(String(100), nullable=True)
    worker_pid = Column(Integer, nullable=True)

    # Relationships
    video = relationship("Video", back_populates="processing_jobs")
    user = relationship("User", back_populates="processing_jobs")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name='check_status'
        ),
        CheckConstraint('progress >= 0 AND progress <= 100', name='check_progress_range'),
        CheckConstraint('retry_count >= 0', name='check_retry_count_positive'),
        Index('idx_job_status_priority', 'status', 'priority'),
        Index('idx_job_user_status', 'user_id', 'status'),
    )

    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, video_id={self.video_id}, type='{self.job_type}', status='{self.status}')>"


class Session(Base, TimestampMixin):
    """User session model for JWT tracking"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Session info
    token_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA256 of JWT
    refresh_token_hash = Column(String(64), unique=True, nullable=True, index=True)

    # Client info
    ip_address = Column(String(45), nullable=False)  # IPv6 compatible
    user_agent = Column(String(512), nullable=True)

    # Timing
    expires_at = Column(DateTime, nullable=False, index=True)
    last_activity = Column(DateTime, nullable=False, server_default=func.now())

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoke_reason = Column(String(100), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

    # Constraints
    __table_args__ = (
        Index('idx_user_active', 'user_id', 'is_active'),
        Index('idx_expires', 'expires_at'),
    )

    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at

    def revoke(self, reason: str = "user_logout") -> None:
        """Revoke this session"""
        self.is_active = False
        self.revoked_at = datetime.utcnow()
        self.revoke_reason = reason

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at}, active={self.is_active})>"


class AuditLog(Base):
    """Audit log for all user and admin actions"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Action info
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)  # video, user, settings, etc.
    resource_id = Column(Integer, nullable=True)

    # Details
    details = Column(JSON, nullable=True)  # Additional context

    # Request info
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(String(512), nullable=True)

    # Timing
    timestamp = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    # Severity
    severity = Column(String(20), default='info', nullable=False)  # info, warning, error, critical

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warning', 'error', 'critical')",
            name='check_severity'
        ),
        Index('idx_action_timestamp', 'action', 'timestamp'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_resource', 'resource_type', 'resource_id'),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', user_id={self.user_id}, timestamp={self.timestamp})>"


class UserPreference(Base, TimestampMixin):
    """User-specific preferences (overrides user.json defaults)"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Preferences stored as JSON
    preferences = Column(JSON, nullable=False, default=dict)

    # Constraints
    __table_args__ = (
        Index('idx_user', 'user_id'),
    )

    def __repr__(self):
        return f"<UserPreference(user_id={self.user_id})>"
