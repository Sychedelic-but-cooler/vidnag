"""
WebSocket Routes
Real-time communication endpoints
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional

from backend.core.logging import get_logger
from backend.models import User
from backend.utils.dependencies import get_db_session
from backend.utils.jwt_utils import decode_access_token


router = APIRouter(tags=["websockets"])


async def get_current_user_ws(
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db_session)
) -> Optional[User]:
    """
    Get current user from WebSocket token

    WebSocket authentication via query parameter
    """
    logger = get_logger()

    try:
        # Decode token
        payload = decode_access_token(token)
        if not payload:
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        return user

    except Exception as e:
        logger.app.error(f"WebSocket auth error: {e}")
        return None


@router.websocket("/ws/downloads")
async def websocket_downloads(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token")
):
    """
    WebSocket endpoint for real-time download progress updates

    Connect with: ws://host/ws/downloads?token=YOUR_JWT_TOKEN

    Messages sent to client:
    {
        "type": "download_progress",
        "job_id": 123,
        "status": "running",
        "progress": 45.2,
        "current_step": "Downloading: 45.2%",
        "download_speed": "5.2MiB/s",
        "download_eta": "02:30",
        "total_size": "150MiB",
        "video": {...},
        "error_message": null
    }

    Client should send periodic ping messages to keep connection alive:
    {"type": "ping"}

    Server will respond with:
    {"type": "pong"}
    """
    logger = get_logger()

    # Get WebSocket manager from app state
    ws_manager = websocket.app.state.ws_manager

    # Authenticate user
    db = next(get_db_session())
    try:
        user = await get_current_user_ws(token, db)
        if not user:
            await websocket.close(code=4001, reason="Authentication failed")
            return

        # Register connection
        await ws_manager.connect(websocket, user.id)

        try:
            # Keep connection alive and handle client messages
            while True:
                try:
                    data = await websocket.receive_json()

                    # Handle ping/pong for keepalive
                    if data.get('type') == 'ping':
                        await websocket.send_json({'type': 'pong'})

                except WebSocketDisconnect:
                    logger.app.info(f"WebSocket disconnected for user {user.id}")
                    break
                except Exception as e:
                    logger.app.error(f"Error receiving WebSocket message: {e}")
                    break

        finally:
            await ws_manager.disconnect(websocket, user.id)

    except Exception as e:
        logger.app.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass
    finally:
        db.close()
