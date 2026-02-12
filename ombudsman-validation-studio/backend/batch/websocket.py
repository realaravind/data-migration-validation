"""WebSocket endpoint for real-time batch job updates."""

import asyncio
import json
import logging
from typing import Set, Dict
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)


class JobUpdateManager:
    """Manages WebSocket connections and broadcasts job updates."""

    def __init__(self):
        # Map of project_id -> set of connected websockets
        self.connections: Dict[str, Set[WebSocket]] = {}
        # Global connections (no project filter)
        self.global_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, project_id: str = None):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if project_id:
            if project_id not in self.connections:
                self.connections[project_id] = set()
            self.connections[project_id].add(websocket)
            logger.info(f"WebSocket connected for project: {project_id}")
        else:
            self.global_connections.add(websocket)
            logger.info("WebSocket connected (global)")

    def disconnect(self, websocket: WebSocket, project_id: str = None):
        """Remove a WebSocket connection."""
        if project_id and project_id in self.connections:
            self.connections[project_id].discard(websocket)
            if not self.connections[project_id]:
                del self.connections[project_id]
        self.global_connections.discard(websocket)
        logger.info(f"WebSocket disconnected")

    async def broadcast_job_update(self, job_data: dict, project_id: str = None):
        """Broadcast job update to relevant connections."""
        message = json.dumps({
            "type": "job_update",
            "timestamp": datetime.utcnow().isoformat(),
            "data": job_data
        })

        # Send to project-specific connections
        if project_id and project_id in self.connections:
            disconnected = set()
            for connection in self.connections[project_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.warning(f"Failed to send to websocket: {e}")
                    disconnected.add(connection)
            # Clean up disconnected
            for conn in disconnected:
                self.connections[project_id].discard(conn)

        # Send to global connections
        disconnected = set()
        for connection in self.global_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to global websocket: {e}")
                disconnected.add(connection)
        # Clean up disconnected
        for conn in disconnected:
            self.global_connections.discard(conn)

    async def broadcast_job_completed(self, job_id: str, status: str, job_name: str, project_id: str = None):
        """Broadcast job completion notification."""
        await self.broadcast_job_update({
            "job_id": job_id,
            "status": status,
            "name": job_name,
            "event": "job_completed"
        }, project_id)

    async def broadcast_job_progress(self, job_id: str, progress: dict, project_id: str = None):
        """Broadcast job progress update."""
        await self.broadcast_job_update({
            "job_id": job_id,
            "progress": progress,
            "event": "job_progress"
        }, project_id)

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        count = len(self.global_connections)
        for conns in self.connections.values():
            count += len(conns)
        return count


# Singleton instance
job_update_manager = JobUpdateManager()
