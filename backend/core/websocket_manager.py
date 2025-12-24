"""
WebSocket Manager
Manages WebSocket connections and broadcasts download progress updates
"""

import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from backend.core.logging import get_logger


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        # Map user_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.logger = get_logger()
        self._lock = asyncio.Lock()

        # Store the main event loop for thread-safe broadcasts
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = None

    async def connect(self, websocket: WebSocket, user_id: int):
        """Register a new WebSocket connection for a user"""
        await websocket.accept()

        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)

        self.logger.app.info(f"WebSocket connected for user {user_id}")

    async def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection"""
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

        self.logger.app.info(f"WebSocket disconnected for user {user_id}")

    async def broadcast_to_user(self, user_id: int, message: dict):
        """Send a message to all WebSocket connections for a specific user"""
        if user_id not in self.active_connections:
            return

        # Create a copy of the set to avoid modification during iteration
        async with self._lock:
            connections = self.active_connections.get(user_id, set()).copy()

        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                self.logger.app.error(f"Error sending WebSocket message: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                if user_id in self.active_connections:
                    for conn in disconnected:
                        self.active_connections[user_id].discard(conn)
                    if not self.active_connections[user_id]:
                        del self.active_connections[user_id]

    def broadcast_to_user_sync(self, user_id: int, message: dict):
        """
        Synchronous wrapper for broadcast_to_user

        This is called from worker threads, so we need to schedule
        the coroutine in the main event loop safely.
        """
        if not self._loop:
            # No event loop available - skip WebSocket update
            return

        try:
            # Schedule the coroutine in the main event loop from worker thread
            # Use run_coroutine_threadsafe for thread-safe execution
            asyncio.run_coroutine_threadsafe(
                self.broadcast_to_user(user_id, message),
                self._loop
            )
        except Exception as e:
            self.logger.app.error(f"Error in sync broadcast: {e}")

    async def send_download_progress(
        self,
        user_id: int,
        job_id: int,
        status: str,
        progress: float,
        current_step: str,
        download_speed: str = None,
        download_eta: str = None,
        total_size: str = None,
        video: dict = None,
        error_message: str = None
    ):
        """Send download progress update to user"""
        message = {
            'type': 'download_progress',
            'job_id': job_id,
            'status': status,
            'progress': progress,
            'current_step': current_step,
            'download_speed': download_speed,
            'download_eta': download_eta,
            'total_size': total_size,
            'video': video,
            'error_message': error_message
        }

        await self.broadcast_to_user(user_id, message)
