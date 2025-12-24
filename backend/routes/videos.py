"""
Video Routes
API endpoints for video downloads and management
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from typing import Optional, List

from backend.core.logging import get_logger
from backend.core.ip_extraction import get_client_ip
from backend.models import User
from backend.utils.dependencies import get_db_session, get_current_user
from backend.services.video_download_service import VideoDownloadService, DownloadServiceError


router = APIRouter(prefix="/api/videos", tags=["videos"])


# === Request/Response Models ===

class DownloadRequest(BaseModel):
    """Video download request"""
    url: str
    title: Optional[str] = None
    visibility: str = 'private'


class DownloadResponse(BaseModel):
    """Video download response"""
    job_id: int
    video_id: int
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """Job status response"""
    job_id: int
    status: str
    progress: float
    current_step: Optional[str]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]
    video: Optional[dict]


class VideoInfo(BaseModel):
    """Video information"""
    id: int
    title: str
    status: str
    visibility: str
    source_type: str
    source_url: Optional[str]
    file_size: int
    duration: Optional[float]
    format: Optional[str]
    created_at: Optional[str]
    error_message: Optional[str]


class VideoList(BaseModel):
    """List of videos with pagination"""
    videos: List[VideoInfo]
    total: int
    page: int
    per_page: int
    total_pages: int


class VideoDetail(BaseModel):
    """Detailed video information"""
    id: int
    title: str
    description: Optional[str]
    status: str
    visibility: str
    source_type: str
    source_url: Optional[str]
    file_path: str
    file_size: int
    checksum: Optional[str]
    duration: Optional[float]
    format: Optional[str]
    codec_video: Optional[str]
    codec_audio: Optional[str]
    width: Optional[int]
    height: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]
    error_message: Optional[str]


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


# === Dependencies ===

def get_download_service(request: Request) -> VideoDownloadService:
    """Get video download service from app state"""
    if not hasattr(request.app.state, 'download_service'):
        raise HTTPException(
            status_code=503,
            detail="Download service not initialized"
        )
    return request.app.state.download_service


# === Routes ===

@router.post("/download", response_model=DownloadResponse)
def submit_download(
    data: DownloadRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
    download_service: VideoDownloadService = Depends(get_download_service)
):
    """
    Submit a video download

    Creates a download job and returns immediately. The download
    runs in the background and can be monitored via the job status endpoint.

    Rate limited: 20 downloads per hour per user (configured in settings)

    Privacy: visibility defaults to 'private' if not specified
    """
    logger = get_logger()
    ip = get_client_ip(request)

    try:
        # Submit download
        job, video = download_service.submit_download(
            db=db,
            user_id=user.id,
            url=data.url,
            title=data.title,
            visibility=data.visibility
        )

        # Log action
        logger.log_user_action(
            action="video_download_submitted",
            user_id=user.id,
            details={
                "job_id": job.id,
                "video_id": video.id,
                "url": data.url,
                "visibility": data.visibility
            },
            ip=ip
        )

        return DownloadResponse(
            job_id=job.id,
            video_id=video.id,
            status=job.status,
            message="Download queued successfully"
        )

    except DownloadServiceError as e:
        logger.log_user_action(
            action="video_download_failed",
            user_id=user.id,
            details={"url": data.url, "error": str(e)},
            ip=ip
        )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.app.error(f"Unexpected error submitting download: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/download/{job_id}", response_model=JobStatusResponse)
def get_download_status(
    job_id: int,
    db: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
    download_service: VideoDownloadService = Depends(get_download_service)
):
    """
    Get download job status

    Returns real-time progress information for a download job.
    Includes video details when download is complete.

    Privacy: Owner or admin only
    """
    try:
        status = download_service.get_download_status(
            db=db,
            job_id=job_id,
            user_id=user.id,
            is_admin=user.is_admin
        )

        return JobStatusResponse(**status)

    except DownloadServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "access denied" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger = get_logger()
        logger.app.error(f"Error getting download status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=VideoList)
def list_videos(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    source_type: Optional[str] = Query(None, description="Filter by source type (download/upload)"),
    visibility: Optional[str] = Query(None, description="Filter by visibility (private/unlisted/public)"),
    db: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
    download_service: VideoDownloadService = Depends(get_download_service)
):
    """
    List videos

    Returns paginated list of videos with privacy filtering.

    Privacy:
    - Non-admin users: Only see their own videos
    - Admin users: See all videos across all users

    Can filter by source_type and visibility.
    """
    try:
        result = download_service.list_videos(
            db=db,
            user_id=user.id,
            is_admin=user.is_admin,
            page=page,
            per_page=per_page,
            source_type=source_type,
            visibility=visibility
        )

        return VideoList(**result)

    except DownloadServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger = get_logger()
        logger.app.error(f"Error listing videos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{video_id}", response_model=VideoDetail)
def get_video(
    video_id: int,
    db: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
    download_service: VideoDownloadService = Depends(get_download_service)
):
    """
    Get video details

    Returns full information about a specific video.

    Privacy: Owner or admin only
    Checks Video.user_id == current_user.id OR current_user.is_admin
    """
    try:
        video = download_service.get_video(
            db=db,
            video_id=video_id,
            user_id=user.id,
            is_admin=user.is_admin
        )

        return VideoDetail(**video)

    except DownloadServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "access denied" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger = get_logger()
        logger.app.error(f"Error getting video: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{video_id}", response_model=MessageResponse)
def delete_video(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
    download_service: VideoDownloadService = Depends(get_download_service)
):
    """
    Delete video

    Marks video as deleted and decrements user storage quota.
    Actual file cleanup happens in the background.

    Privacy: Owner or admin only
    """
    logger = get_logger()
    ip = get_client_ip(request)

    try:
        download_service.delete_video(
            db=db,
            video_id=video_id,
            user_id=user.id,
            is_admin=user.is_admin
        )

        # Log action
        logger.log_user_action(
            action="video_deleted",
            user_id=user.id,
            details={"video_id": video_id},
            ip=ip
        )

        return MessageResponse(message="Video deleted successfully")

    except DownloadServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "access denied" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.app.error(f"Error deleting video: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/queue/status")
def get_queue_status(
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    Get download queue status

    Returns information about active and pending downloads.
    Admin-only endpoint for monitoring the download queue.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )

    # Get download manager from app state
    if not hasattr(request.app.state, 'download_manager'):
        raise HTTPException(
            status_code=503,
            detail="Download manager not initialized"
        )

    download_manager = request.app.state.download_manager
    status = download_manager.get_queue_status()

    return status
