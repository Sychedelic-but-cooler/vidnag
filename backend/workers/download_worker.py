"""
Download Worker
Executes individual video download jobs using yt-dlp
"""

import subprocess
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import traceback

from backend.utils.ytdlp_wrapper import YtDlpWrapper, YtDlpError
from backend.utils.file_operations import (
    calculate_file_checksum,
    safe_move_file,
    get_file_size,
    FileOperationError
)
from backend.models import Video, ProcessingJob


class DownloadWorker:
    """Executes individual video downloads"""

    def __init__(self, db_manager, settings_manager, logger):
        """
        Initialize download worker

        Args:
            db_manager: Database manager for session handling
            settings_manager: Settings manager for configuration
            logger: Logger instance
        """
        self.db = db_manager
        self.settings = settings_manager
        self.logger = logger

    def execute_download(self, job_id: int) -> bool:
        """
        Execute a download job

        Args:
            job_id: ID of the ProcessingJob to execute

        Returns:
            True if download succeeded, False otherwise
        """
        video_id = None
        temp_output_path = None

        try:
            # Get job details from database
            with self.db.session_scope() as session:
                job = session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                if not job:
                    self.logger.error(f"Job {job_id} not found")
                    return False

                video_id = job.video_id
                video = session.query(Video).filter(Video.id == video_id).first()
                if not video:
                    self.logger.error(f"Video {video_id} not found for job {job_id}")
                    return False

                url = video.source_url
                user_id = video.user_id

                # Update job status
                job.status = 'running'
                job.current_step = 'Initializing download'
                job.progress = 0.0
                session.commit()

                self.logger.info(f"Starting download for job {job_id}, video {video_id}, URL: {url}")

            # Get settings
            from backend.core.settings import SettingsLevel
            temp_path = self.settings.get(SettingsLevel.APP, "storage.temp_path", "/var/vidnag/temp")
            max_size_mb = self.settings.get(SettingsLevel.ADMIN, "downloads.max_download_size_mb", 1000)
            timeout_seconds = self.settings.get(SettingsLevel.ADMIN, "downloads.timeout_seconds", 300)

            # Generate temporary output path
            temp_filename = Path(video.file_path).name
            temp_output_template = os.path.join(temp_path, f"{Path(temp_filename).stem}.%(ext)s")

            # Update progress
            self._update_job_progress(job_id, 5.0, 'Starting download')

            # Build yt-dlp command
            cmd = YtDlpWrapper.build_download_command(
                url=url,
                output_path=temp_output_template,
                max_size_mb=max_size_mb
            )

            self.logger.info(f"Executing yt-dlp command: {' '.join(cmd)}")

            # Execute download with progress monitoring
            temp_output_path = self._execute_download_subprocess(
                cmd, job_id, timeout_seconds, temp_output_template
            )

            if not temp_output_path or not os.path.exists(temp_output_path):
                raise Exception("Download completed but output file not found")

            self.logger.info(f"Download completed: {temp_output_path}")

            # Update progress
            self._update_job_progress(job_id, 70.0, 'Calculating checksum')

            # Calculate file size and checksum
            file_size = get_file_size(temp_output_path)
            checksum = calculate_file_checksum(temp_output_path)

            self.logger.info(f"File size: {file_size} bytes, checksum: {checksum}")

            # Update progress
            self._update_job_progress(job_id, 80.0, 'Moving to storage')

            # Move to final storage location
            storage_path = self.settings.get(SettingsLevel.APP, "storage.base_path", "/var/vidnag/storage")
            video_storage_dir = os.path.join(storage_path, "videos")

            final_path = safe_move_file(
                temp_output_path,
                video_storage_dir,
                Path(video.file_path).name,
                storage_root=storage_path
            )

            self.logger.info(f"File moved to: {final_path}")

            # Update progress
            self._update_job_progress(job_id, 90.0, 'Updating database')

            # Update video and job in database
            with self.db.session_scope() as session:
                video = session.query(Video).filter(Video.id == video_id).first()
                job = session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

                # Update video
                video.status = 'ready'
                video.file_path = final_path
                video.file_size = file_size
                video.checksum = checksum
                video.error_message = None

                # Update job
                job.status = 'completed'
                job.progress = 100.0
                job.current_step = 'Completed'
                job.completed_at = datetime.utcnow()

                # Update user storage
                user = session.query(video.user.__class__).filter_by(id=user_id).first()
                if user:
                    user.storage_used += file_size

                session.commit()

            self.logger.info(f"Job {job_id} completed successfully")
            return True

        except subprocess.CalledProcessError as e:
            error_msg = self._handle_subprocess_error(e, job_id, video_id, temp_output_path)
            self.logger.error(f"Job {job_id} failed: {error_msg}")
            return False

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            error_trace = traceback.format_exc()
            self.logger.error(f"Job {job_id} failed with exception: {error_msg}\n{error_trace}")

            self._mark_job_failed(job_id, error_msg, error_trace)
            return False

    def _execute_download_subprocess(
        self,
        cmd: list,
        job_id: int,
        timeout: int,
        output_template: str
    ) -> Optional[str]:
        """
        Execute yt-dlp subprocess and monitor progress

        Args:
            cmd: Command to execute
            job_id: Job ID for progress updates
            timeout: Timeout in seconds
            output_template: Output path template to determine final filename

        Returns:
            Path to downloaded file or None

        Raises:
            subprocess.CalledProcessError: If download fails
            subprocess.TimeoutExpired: If timeout is exceeded
        """
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        last_progress_update = time.time()
        output_lines = []

        try:
            # Monitor output
            for line in process.stdout:
                output_lines.append(line)

                # Parse progress
                progress_info = YtDlpWrapper.parse_progress_line(line)
                if progress_info and progress_info.get('percent'):
                    # Update progress (scale 5-70% for download phase)
                    scaled_progress = 5.0 + (progress_info['percent'] * 0.65)

                    # Rate limit updates (every 2 seconds)
                    current_time = time.time()
                    if current_time - last_progress_update >= 2.0:
                        self._update_job_progress(
                            job_id,
                            scaled_progress,
                            f"Downloading: {progress_info['percent']:.1f}%"
                        )
                        last_progress_update = current_time

            # Wait for process to complete
            return_code = process.wait(timeout=timeout)

            if return_code != 0:
                full_output = ''.join(output_lines)
                raise subprocess.CalledProcessError(return_code, cmd, output=full_output)

            # Determine actual output filename
            # yt-dlp replaces %(ext)s with actual extension
            output_file = self._find_downloaded_file(output_template)
            return output_file

        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise

    def _find_downloaded_file(self, template: str) -> Optional[str]:
        """
        Find the actual downloaded file from template

        yt-dlp replaces %(ext)s with actual extension, so we need to find the file

        Args:
            template: Output template with %(ext)s placeholder

        Returns:
            Path to downloaded file or None
        """
        # Get directory and base name without extension placeholder
        directory = os.path.dirname(template)
        base_name = os.path.basename(template).replace('.%(ext)s', '')

        # Look for files matching the base name
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                if filename.startswith(base_name):
                    return os.path.join(directory, filename)

        return None

    def _handle_subprocess_error(
        self,
        error: subprocess.CalledProcessError,
        job_id: int,
        video_id: Optional[int],
        temp_file: Optional[str]
    ) -> str:
        """
        Handle subprocess errors with special handling for size limits

        Args:
            error: The subprocess error
            job_id: Job ID
            video_id: Video ID
            temp_file: Path to temporary file (may be partial)

        Returns:
            Error message string
        """
        error_output = error.output if error.output else ""

        # Check if error is due to file size limit
        if "File is larger than max-filesize" in error_output or "max-filesize" in error_output:
            error_msg = (
                "Video exceeds the download size limit. "
                "Partial download has been saved. "
                "Please contact an administrator to increase your download limit."
            )

            # Keep partial file if it exists
            if temp_file and os.path.exists(temp_file):
                try:
                    file_size = get_file_size(temp_file)
                    checksum = calculate_file_checksum(temp_file)

                    # Move partial file to storage
                    from backend.core.settings import SettingsLevel
                    storage_path = self.settings.get(SettingsLevel.APP, "storage.base_path", "/var/vidnag/storage")
                    video_storage_dir = os.path.join(storage_path, "videos")

                    with self.db.session_scope() as session:
                        video = session.query(Video).filter(Video.id == video_id).first()
                        if video:
                            final_path = safe_move_file(
                                temp_file,
                                video_storage_dir,
                                Path(video.file_path).name,
                                storage_root=storage_path
                            )

                            video.status = 'error'
                            video.error_message = error_msg
                            video.file_path = final_path
                            video.file_size = file_size
                            video.checksum = checksum

                            session.commit()

                except Exception as e:
                    self.logger.error(f"Failed to save partial download: {e}")

            self._mark_job_failed(job_id, error_msg, error_output)
            return error_msg

        # Handle other errors
        elif "Unsupported URL" in error_output or "is not a valid URL" in error_output:
            error_msg = "This URL is not supported or is invalid"
        elif "Video unavailable" in error_output:
            error_msg = "Video is unavailable or has been removed"
        elif "Private video" in error_output:
            error_msg = "Video is private and cannot be downloaded"
        else:
            error_msg = f"Download failed: {error_output[:200]}"  # Limit error message length

        self._mark_job_failed(job_id, error_msg, error_output)
        return error_msg

    def _update_job_progress(self, job_id: int, progress: float, step: str) -> None:
        """Update job progress in database"""
        try:
            with self.db.session_scope() as session:
                job = session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                if job:
                    job.progress = min(progress, 100.0)
                    job.current_step = step
                    session.commit()
        except Exception as e:
            self.logger.error(f"Failed to update job progress: {e}")

    def _mark_job_failed(self, job_id: int, error_message: str, error_trace: str = None) -> None:
        """Mark job as failed in database"""
        try:
            with self.db.session_scope() as session:
                job = session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                if job:
                    job.status = 'failed'
                    job.error_message = error_message
                    if error_trace:
                        job.error_trace = error_trace[:5000]  # Limit trace length
                    job.completed_at = datetime.utcnow()

                    # Also mark video as error
                    if job.video_id:
                        video = session.query(Video).filter(Video.id == job.video_id).first()
                        if video:
                            video.status = 'error'
                            video.error_message = error_message

                    session.commit()
        except Exception as e:
            self.logger.error(f"Failed to mark job as failed: {e}")
