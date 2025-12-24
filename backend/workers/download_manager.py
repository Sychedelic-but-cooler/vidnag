"""
Download Manager
Manages ThreadPoolExecutor and job queue polling for video downloads
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from typing import Dict, Optional

from backend.models import ProcessingJob
from backend.workers.download_worker import DownloadWorker


class DownloadManager:
    """Manages download job queue and worker thread pool"""

    def __init__(self, settings_manager, db_manager, logger, ws_manager=None):
        """
        Initialize download manager

        Args:
            settings_manager: Settings manager instance
            db_manager: Database manager instance
            logger: Logger instance
            ws_manager: WebSocket manager for real-time updates (optional)
        """
        self.settings = settings_manager
        self.db = db_manager
        self.logger = logger
        self.ws_manager = ws_manager

        # Get max workers from settings
        from backend.core.settings import SettingsLevel
        self.max_workers = self.settings.get(
            SettingsLevel.ADMIN,
            "processing.max_concurrent_jobs",
            4
        )

        # Initialize thread pool
        self.executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="dl-worker"
        )

        # Track active jobs: job_id -> Future
        self.active_jobs: Dict[int, Future] = {}
        self.lock = threading.Lock()

        # Shutdown flag
        self.shutdown_flag = threading.Event()
        self.shutdown_requested = False

        # Initialize worker with WebSocket manager
        self.worker = DownloadWorker(db_manager, settings_manager, logger, ws_manager)

        # Start background polling thread
        self.poller_thread = threading.Thread(
            target=self._poll_pending_jobs,
            daemon=True,
            name="download-queue-poller"
        )
        self.poller_thread.start()

        self.logger.app.info(
            f"DownloadManager initialized with {self.max_workers} max workers"
        )

    def _poll_pending_jobs(self):
        """
        Background thread that polls database for pending jobs every 5 seconds

        This continuously checks for available worker slots and schedules
        pending jobs from the database queue.
        """
        self.logger.app.info("Download queue poller started")

        while not self.shutdown_requested:
            try:
                # Wait for 5 seconds or until shutdown/wake signal
                signaled = self.shutdown_flag.wait(timeout=5.0)

                # Clear the flag if it was set (for wake-up signal)
                if signaled:
                    self.shutdown_flag.clear()

                # Check if shutdown was requested
                if self.shutdown_requested:
                    break

                # Check for available slots
                with self.lock:
                    available_slots = self.max_workers - len(self.active_jobs)

                if available_slots > 0:
                    # Schedule pending jobs
                    scheduled = self._schedule_pending_jobs(available_slots)

                    if scheduled > 0:
                        self.logger.app.info(
                            f"Scheduled {scheduled} job(s), "
                            f"{len(self.active_jobs)}/{self.max_workers} workers active"
                        )

            except Exception as e:
                self.logger.app.error(f"Error in queue polling loop: {e}", exc_info=True)

        self.logger.app.info("Download queue poller stopped")

    def _schedule_pending_jobs(self, count: int) -> int:
        """
        Fetch pending jobs from database and submit to ThreadPool

        Args:
            count: Maximum number of jobs to schedule

        Returns:
            Number of jobs actually scheduled
        """
        scheduled_count = 0

        try:
            with self.db.session_scope() as session:
                # Fetch pending download jobs, ordered by priority and creation time
                pending_jobs = session.query(ProcessingJob).filter(
                    ProcessingJob.job_type == 'download',
                    ProcessingJob.status == 'pending'
                ).order_by(
                    ProcessingJob.priority.desc(),
                    ProcessingJob.created_at.asc()
                ).limit(count).all()

                for job in pending_jobs:
                    try:
                        # Submit job to thread pool
                        future = self.executor.submit(self._execute_job_wrapper, job.id)

                        # Add completion callback
                        future.add_done_callback(
                            lambda f, jid=job.id: self._cleanup_job(jid, f)
                        )

                        # Track active job
                        with self.lock:
                            self.active_jobs[job.id] = future

                        # Update job status in database
                        job.status = 'running'
                        job.started_at = datetime.utcnow()
                        session.commit()

                        scheduled_count += 1

                        self.logger.app.info(
                            f"Scheduled job {job.id} for video {job.video_id}"
                        )

                    except Exception as e:
                        self.logger.app.error(
                            f"Failed to schedule job {job.id}: {e}",
                            exc_info=True
                        )

        except Exception as e:
            self.logger.app.error(f"Failed to fetch pending jobs: {e}", exc_info=True)

        return scheduled_count

    def _execute_job_wrapper(self, job_id: int) -> bool:
        """
        Wrapper for job execution (runs in thread pool)

        Args:
            job_id: ID of job to execute

        Returns:
            True if job succeeded, False otherwise
        """
        try:
            self.logger.app.info(f"Worker thread starting job {job_id}")
            success = self.worker.execute_download(job_id)

            if success:
                self.logger.app.info(f"Worker thread completed job {job_id} successfully")
            else:
                self.logger.app.warning(f"Worker thread completed job {job_id} with failure")

            return success

        except Exception as e:
            self.logger.app.error(
                f"Worker thread failed for job {job_id}: {e}",
                exc_info=True
            )
            return False

    def _cleanup_job(self, job_id: int, future: Future):
        """
        Cleanup after job completion (called by future callback)

        Args:
            job_id: ID of completed job
            future: The completed future object
        """
        try:
            # Remove from active jobs
            with self.lock:
                self.active_jobs.pop(job_id, None)

            # Check if future raised an exception
            try:
                future.result()  # This will raise if the job raised
            except Exception as e:
                self.logger.app.error(
                    f"Job {job_id} raised exception: {e}",
                    exc_info=True
                )

            self.logger.app.debug(
                f"Cleaned up job {job_id}, "
                f"{len(self.active_jobs)}/{self.max_workers} workers active"
            )

            # Trigger immediate re-check for pending jobs
            # This ensures we don't wait 5 seconds if there are pending jobs
            self.shutdown_flag.set()

        except Exception as e:
            self.logger.app.error(f"Error cleaning up job {job_id}: {e}", exc_info=True)

    def notify_job_submitted(self):
        """
        Notify manager that a new job was submitted

        This triggers an immediate check for pending jobs instead of
        waiting for the next polling interval.
        """
        self.logger.app.debug("Job submission notification received")
        self.shutdown_flag.set()

    def get_queue_status(self) -> Dict:
        """
        Get current queue status

        Returns:
            Dictionary with queue statistics:
            - active_jobs: Number of currently running jobs
            - max_workers: Maximum concurrent jobs
            - available_slots: Number of available worker slots
        """
        with self.lock:
            active_count = len(self.active_jobs)

        # Get pending count from database
        try:
            with self.db.session_scope(read_only=True) as session:
                pending_count = session.query(ProcessingJob).filter(
                    ProcessingJob.job_type == 'download',
                    ProcessingJob.status == 'pending'
                ).count()
        except Exception as e:
            self.logger.app.error(f"Failed to get pending count: {e}")
            pending_count = 0

        return {
            'active_jobs': active_count,
            'pending_jobs': pending_count,
            'max_workers': self.max_workers,
            'available_slots': self.max_workers - active_count
        }

    def shutdown(self, wait: bool = True, timeout: Optional[float] = 30.0):
        """
        Shutdown the download manager

        Args:
            wait: Whether to wait for active jobs to complete
            timeout: Maximum time to wait in seconds (None = wait indefinitely)
        """
        self.logger.app.info("Shutting down DownloadManager...")

        # Signal shutdown to poller thread
        self.shutdown_requested = True
        self.shutdown_flag.set()

        # Wait for poller thread to finish
        if self.poller_thread.is_alive():
            self.poller_thread.join(timeout=5.0)

        # Shutdown thread pool
        self.executor.shutdown(wait=wait, cancel_futures=not wait)

        if wait:
            self.logger.app.info("DownloadManager shutdown complete (waited for jobs)")
        else:
            self.logger.app.info("DownloadManager shutdown complete (cancelled pending jobs)")

    def cancel_job(self, job_id: int) -> bool:
        """
        Attempt to cancel a job

        Args:
            job_id: ID of job to cancel

        Returns:
            True if job was cancelled, False if already running/completed
        """
        with self.lock:
            future = self.active_jobs.get(job_id)

        if future:
            # Try to cancel the future
            cancelled = future.cancel()

            if cancelled:
                self.logger.app.info(f"Cancelled job {job_id}")

                # Update job status in database
                try:
                    with self.db.session_scope() as session:
                        job = session.query(ProcessingJob).filter(
                            ProcessingJob.id == job_id
                        ).first()

                        if job:
                            job.status = 'cancelled'
                            job.completed_at = datetime.utcnow()
                            session.commit()
                except Exception as e:
                    self.logger.app.error(f"Failed to update cancelled job {job_id}: {e}")

                return True
            else:
                self.logger.app.warning(
                    f"Could not cancel job {job_id} (already running)"
                )
                return False
        else:
            # Job not in active jobs, might be pending
            try:
                with self.db.session_scope() as session:
                    job = session.query(ProcessingJob).filter(
                        ProcessingJob.id == job_id,
                        ProcessingJob.status == 'pending'
                    ).first()

                    if job:
                        job.status = 'cancelled'
                        job.completed_at = datetime.utcnow()
                        session.commit()
                        self.logger.app.info(f"Cancelled pending job {job_id}")
                        return True
            except Exception as e:
                self.logger.app.error(f"Failed to cancel pending job {job_id}: {e}")

            return False
