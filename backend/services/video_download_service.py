"""
Video Download Service
High-level orchestration for video download operations
"""

from typing import Dict, Optional, Any, Tuple
from datetime import datetime

from backend.models import Video, ProcessingJob, User
from backend.utils.validation import URLValidator
from backend.utils.ytdlp_wrapper import YtDlpWrapper, YtDlpError
from backend.utils.file_operations import generate_video_uuid
from sqlalchemy.orm import Session


class DownloadServiceError(Exception):
    """Custom exception for download service errors"""
    pass


class VideoDownloadService:
    """Service for managing video downloads"""

    def __init__(self, settings_manager, db_manager, download_manager, logger):
        """
        Initialize video download service

        Args:
            settings_manager: Settings manager instance
            db_manager: Database manager instance
            download_manager: Download manager instance (manages worker pool)
            logger: Logger instance
        """
        self.settings = settings_manager
        self.db = db_manager
        self.download_manager = download_manager
        self.logger = logger

        # Initialize URL validator
        self.url_validator = URLValidator(settings_manager)

    def submit_download(
        self,
        db: Session,
        user_id: int,
        url: str,
        title: Optional[str] = None,
        visibility: str = 'private'
    ) -> Tuple[ProcessingJob, Video]:
        """
        Submit a video download to the queue

        Steps:
        1. Validate URL (scheme, domain whitelist)
        2. Get video info via yt-dlp (check size estimate)
        3. Check user storage quota
        4. Generate UUID filename
        5. Create Video record (status='processing', source_type='download')
        6. Create ProcessingJob (status='pending', job_type='download')
        7. Notify DownloadManager to check queue
        8. Return ProcessingJob and Video

        Args:
            db: Database session
            user_id: ID of user submitting download
            url: Video URL to download
            title: Optional custom title (defaults to video title from metadata)
            visibility: Visibility setting ('private', 'unlisted', 'public')

        Returns:
            Tuple of (ProcessingJob, Video)

        Raises:
            DownloadServiceError: If validation fails or quota exceeded
        """
        # Validate visibility
        if visibility not in ('private', 'unlisted', 'public'):
            raise DownloadServiceError(
                f"Invalid visibility '{visibility}'. Must be 'private', 'unlisted', or 'public'"
            )

        # Step 1: Validate URL
        is_valid, error_msg = self.url_validator.validate(url)
        if not is_valid:
            raise DownloadServiceError(f"Invalid URL: {error_msg}")

        # Step 2: Get video info (with timeout)
        self.logger.app.info(f"Fetching video info for URL: {url}")

        try:
            video_info = YtDlpWrapper.get_video_info(url, timeout=30)
        except YtDlpError as e:
            raise DownloadServiceError(f"Failed to get video information: {str(e)}")
        except Exception as e:
            raise DownloadServiceError(f"Unexpected error fetching video info: {str(e)}")

        # Extract video metadata
        video_title = title if title else video_info.get('title', 'Unknown Title')
        duration = video_info.get('duration')
        estimated_size = video_info.get('filesize') or video_info.get('filesize_approx')
        ext = video_info.get('ext', 'mp4')

        self.logger.app.info(
            f"Video info: title='{video_title}', duration={duration}s, "
            f"estimated_size={estimated_size} bytes"
        )

        # Step 3: Check user storage quota
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise DownloadServiceError("User not found")

        # If we have size estimate, check quota
        if estimated_size:
            available_storage = user.storage_quota - user.storage_used

            if estimated_size > available_storage:
                raise DownloadServiceError(
                    f"Insufficient storage quota. "
                    f"Required: {estimated_size / (1024**3):.2f} GB, "
                    f"Available: {available_storage / (1024**3):.2f} GB"
                )

        # Step 4: Generate UUID filename
        uuid_filename = generate_video_uuid(ext)

        # Get storage path from settings
        from backend.core.settings import SettingsLevel
        storage_path = self.settings.get(
            SettingsLevel.APP,
            "storage.base_path",
            "storage"
        )

        import os
        file_path = os.path.join(storage_path, "videos", uuid_filename)

        # Step 5: Create Video record
        video = Video(
            user_id=user_id,
            title=video_title,
            original_filename=f"{video_title[:200]}.{ext}",  # Limit length
            file_path=file_path,
            file_size=0,  # Will be updated after download
            source_type='download',
            source_url=url,
            visibility=visibility,
            status='processing',
            duration=duration,
            format=ext
        )

        db.add(video)
        db.flush()  # Get video.id without committing

        # Step 6: Create ProcessingJob
        job = ProcessingJob(
            video_id=video.id,
            user_id=user_id,
            job_type='download',
            status='pending',
            priority=0,
            progress=0.0,
            current_step='Queued',
            input_params={
                'url': url,
                'title': video_title,
                'visibility': visibility
            }
        )

        db.add(job)
        db.commit()

        self.logger.app.info(
            f"Created download job {job.id} for video {video.id}, "
            f"user {user_id}, URL: {url}"
        )

        # Step 7: Notify DownloadManager
        self.download_manager.notify_job_submitted()

        return job, video

    def get_download_status(
        self,
        db: Session,
        job_id: int,
        user_id: int,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Get status of a download job

        Privacy: Non-admin users can only view their own jobs.
                 Admins can view all jobs.

        Args:
            db: Database session
            job_id: ID of job to query
            user_id: ID of requesting user
            is_admin: Whether requesting user is admin

        Returns:
            Dictionary with job and video details

        Raises:
            DownloadServiceError: If job not found or access denied
        """
        # Fetch job
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

        if not job:
            raise DownloadServiceError("Job not found")

        # Privacy check
        if not is_admin and job.user_id != user_id:
            raise DownloadServiceError("Access denied")

        # Fetch associated video
        video = db.query(Video).filter(Video.id == job.video_id).first()

        # Build response
        response = {
            'job_id': job.id,
            'status': job.status,
            'progress': job.progress,
            'current_step': job.current_step,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'error_message': job.error_message,
            'video': None
        }

        if video:
            response['video'] = {
                'id': video.id,
                'title': video.title,
                'status': video.status,
                'visibility': video.visibility,
                'file_size': video.file_size,
                'duration': video.duration,
                'format': video.format,
                'source_url': video.source_url,
                'error_message': video.error_message
            }

        return response

    def list_videos(
        self,
        db: Session,
        user_id: int,
        is_admin: bool = False,
        page: int = 1,
        per_page: int = 20,
        source_type: Optional[str] = None,
        visibility: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List videos with privacy filtering

        Privacy Rules:
        - Non-admin users: Only see their own videos (all visibilities)
        - Admin users: See all videos across all users
        - Filter by source_type ('download' or 'upload')
        - Filter by visibility ('private', 'unlisted', 'public')

        Args:
            db: Database session
            user_id: ID of requesting user
            is_admin: Whether requesting user is admin
            page: Page number (1-indexed)
            per_page: Results per page
            source_type: Optional filter by source type
            visibility: Optional filter by visibility

        Returns:
            Dictionary with videos list and pagination info
        """
        # Build query
        query = db.query(Video)

        # Privacy filtering
        if not is_admin:
            query = query.filter(Video.user_id == user_id)

        # Source type filter
        if source_type:
            if source_type not in ('download', 'upload'):
                raise DownloadServiceError(
                    f"Invalid source_type '{source_type}'. Must be 'download' or 'upload'"
                )
            query = query.filter(Video.source_type == source_type)

        # Visibility filter
        if visibility:
            if visibility not in ('private', 'unlisted', 'public'):
                raise DownloadServiceError(
                    f"Invalid visibility '{visibility}'. Must be 'private', 'unlisted', or 'public'"
                )
            query = query.filter(Video.visibility == visibility)

        # Exclude deleted videos
        query = query.filter(Video.status != 'deleted')

        # Get total count
        total = query.count()

        # Apply pagination
        query = query.order_by(Video.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        # Execute query
        videos = query.all()

        # Build response
        return {
            'videos': [
                {
                    'id': v.id,
                    'title': v.title,
                    'status': v.status,
                    'visibility': v.visibility,
                    'source_type': v.source_type,
                    'source_url': v.source_url,
                    'file_size': v.file_size,
                    'duration': v.duration,
                    'format': v.format,
                    'created_at': v.created_at.isoformat() if v.created_at else None,
                    'error_message': v.error_message
                }
                for v in videos
            ],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }

    def get_video(
        self,
        db: Session,
        video_id: int,
        user_id: int,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Get video details

        Privacy: Owner or admin only

        Args:
            db: Database session
            video_id: ID of video to retrieve
            user_id: ID of requesting user
            is_admin: Whether requesting user is admin

        Returns:
            Dictionary with video details

        Raises:
            DownloadServiceError: If video not found or access denied
        """
        video = db.query(Video).filter(Video.id == video_id).first()

        if not video:
            raise DownloadServiceError("Video not found")

        # Privacy check
        if not is_admin and video.user_id != user_id:
            raise DownloadServiceError("Access denied")

        return {
            'id': video.id,
            'title': video.title,
            'description': video.description,
            'status': video.status,
            'visibility': video.visibility,
            'source_type': video.source_type,
            'source_url': video.source_url,
            'file_path': video.file_path,
            'file_size': video.file_size,
            'checksum': video.checksum,
            'duration': video.duration,
            'format': video.format,
            'codec_video': video.codec_video,
            'codec_audio': video.codec_audio,
            'width': video.width,
            'height': video.height,
            'created_at': video.created_at.isoformat() if video.created_at else None,
            'updated_at': video.updated_at.isoformat() if video.updated_at else None,
            'error_message': video.error_message
        }

    def delete_video(
        self,
        db: Session,
        video_id: int,
        user_id: int,
        is_admin: bool = False
    ) -> bool:
        """
        Mark video as deleted

        Privacy: Owner or admin only

        Args:
            db: Database session
            video_id: ID of video to delete
            user_id: ID of requesting user
            is_admin: Whether requesting user is admin

        Returns:
            True if deleted

        Raises:
            DownloadServiceError: If video not found or access denied
        """
        video = db.query(Video).filter(Video.id == video_id).first()

        if not video:
            raise DownloadServiceError("Video not found")

        # Privacy check
        if not is_admin and video.user_id != user_id:
            raise DownloadServiceError("Access denied")

        # Mark as deleted
        video.status = 'deleted'

        # Decrement user storage
        user = db.query(User).filter(User.id == video.user_id).first()
        if user and video.file_size > 0:
            user.storage_used = max(0, user.storage_used - video.file_size)

        db.commit()

        self.logger.app.info(
            f"Video {video_id} marked as deleted by user {user_id}"
        )

        return True
