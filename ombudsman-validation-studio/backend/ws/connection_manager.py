"""
WebSocket Connection Manager

Manages WebSocket connections for real-time pipeline execution updates.
Supports multiple concurrent clients with automatic cleanup.
"""

import logging
import asyncio
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Features:
    - Multiple concurrent connections
    - Per-run subscriptions (clients can subscribe to specific runs)
    - Broadcast to all clients or specific run subscribers
    - Automatic connection cleanup
    - Heartbeat/keepalive support
    """

    def __init__(self):
        # All active connections
        self.active_connections: Set[WebSocket] = set()

        # Map of run_id -> set of WebSockets subscribed to that run
        self.run_subscriptions: Dict[str, Set[WebSocket]] = {}

        # Track connection metadata
        self.connection_metadata: Dict[WebSocket, dict] = {}

        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None):
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection to register
            client_id: Optional client identifier
        """
        await websocket.accept()
        self.active_connections.add(websocket)

        # Store metadata
        self.connection_metadata[websocket] = {
            "client_id": client_id or f"client_{id(websocket)}",
            "connected_at": datetime.now().isoformat(),
            "subscriptions": set()
        }

        logger.info(
            f"WebSocket connected: {self.connection_metadata[websocket]['client_id']} "
            f"(Total connections: {len(self.active_connections)})"
        )

        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection_established",
                "client_id": self.connection_metadata[websocket]['client_id'],
                "timestamp": datetime.now().isoformat()
            },
            websocket
        )

    def disconnect(self, websocket: WebSocket):
        """
        Remove and cleanup a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        # Remove from active connections
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Remove from all run subscriptions
        for run_id, subscribers in list(self.run_subscriptions.items()):
            if websocket in subscribers:
                subscribers.remove(websocket)

            # Clean up empty subscription sets
            if not subscribers:
                del self.run_subscriptions[run_id]

        # Remove metadata
        client_id = self.connection_metadata.get(websocket, {}).get("client_id", "unknown")
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]

        logger.info(
            f"WebSocket disconnected: {client_id} "
            f"(Remaining connections: {len(self.active_connections)})"
        )

    def subscribe_to_run(self, websocket: WebSocket, run_id: str):
        """
        Subscribe a WebSocket connection to updates for a specific pipeline run.

        Args:
            websocket: WebSocket connection to subscribe
            run_id: Pipeline run ID to subscribe to
        """
        if run_id not in self.run_subscriptions:
            self.run_subscriptions[run_id] = set()

        self.run_subscriptions[run_id].add(websocket)

        # Update metadata
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].add(run_id)

        logger.debug(
            f"Client {self.connection_metadata.get(websocket, {}).get('client_id', 'unknown')} "
            f"subscribed to run {run_id}"
        )

    def unsubscribe_from_run(self, websocket: WebSocket, run_id: str):
        """
        Unsubscribe a WebSocket connection from a specific pipeline run.

        Args:
            websocket: WebSocket connection to unsubscribe
            run_id: Pipeline run ID to unsubscribe from
        """
        if run_id in self.run_subscriptions and websocket in self.run_subscriptions[run_id]:
            self.run_subscriptions[run_id].remove(websocket)

            # Clean up empty subscription sets
            if not self.run_subscriptions[run_id]:
                del self.run_subscriptions[run_id]

        # Update metadata
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].discard(run_id)

        logger.debug(
            f"Client {self.connection_metadata.get(websocket, {}).get('client_id', 'unknown')} "
            f"unsubscribed from run {run_id}"
        )

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.

        Args:
            message: Message dictionary to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except WebSocketDisconnect:
            logger.warning("WebSocket disconnected while sending personal message")
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message dictionary to broadcast
        """
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                logger.warning("WebSocket disconnected during broadcast")
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_to_run(self, run_id: str, message: dict):
        """
        Broadcast a message to all clients subscribed to a specific pipeline run.

        Args:
            run_id: Pipeline run ID
            message: Message dictionary to broadcast
        """
        if run_id not in self.run_subscriptions:
            logger.debug(f"No subscribers for run {run_id}")
            return

        disconnected = []
        subscribers = self.run_subscriptions[run_id].copy()  # Copy to avoid modification during iteration

        logger.debug(f"Broadcasting to {len(subscribers)} subscribers of run {run_id}")

        for connection in subscribers:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                logger.warning(f"WebSocket disconnected during run broadcast for {run_id}")
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to run {run_id}: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def send_heartbeat(self, websocket: WebSocket):
        """
        Send a heartbeat/ping to check connection health.

        Args:
            websocket: WebSocket connection to ping
        """
        try:
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            self.disconnect(websocket)

    async def heartbeat_loop(self, websocket: WebSocket, interval: int = 30):
        """
        Run a heartbeat loop for a specific connection.

        Args:
            websocket: WebSocket connection
            interval: Heartbeat interval in seconds (default: 30)
        """
        try:
            while websocket in self.active_connections:
                await asyncio.sleep(interval)
                if websocket in self.active_connections:
                    await self.send_heartbeat(websocket)
        except asyncio.CancelledError:
            logger.debug("Heartbeat loop cancelled")
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")

    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)

    def get_run_subscriber_count(self, run_id: str) -> int:
        """Get the number of subscribers for a specific run"""
        return len(self.run_subscriptions.get(run_id, set()))

    def get_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "active_runs": len(self.run_subscriptions),
            "subscriptions": {
                run_id: len(subscribers)
                for run_id, subscribers in self.run_subscriptions.items()
            }
        }


# Global connection manager instance
connection_manager = ConnectionManager()
