"""
WebSocket Router

API endpoints for WebSocket connections.
"""

import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from .connection_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None),
    run_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time pipeline execution updates.

    Query Parameters:
        client_id: Optional client identifier
        run_id: Optional pipeline run ID to subscribe to immediately

    Usage:
        ws = new WebSocket('ws://localhost:8000/ws/pipeline?run_id=run_123')
    """
    await connection_manager.connect(websocket, client_id)

    # Subscribe to run if provided
    if run_id:
        connection_manager.subscribe_to_run(websocket, run_id)
        logger.info(f"Client {client_id} auto-subscribed to run {run_id}")

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(
        connection_manager.heartbeat_loop(websocket, interval=30)
    )

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()

            # Handle client messages
            message_type = data.get("type")

            if message_type == "subscribe":
                # Subscribe to a pipeline run
                target_run_id = data.get("run_id")
                if target_run_id:
                    connection_manager.subscribe_to_run(websocket, target_run_id)
                    await connection_manager.send_personal_message(
                        {
                            "type": "subscribed",
                            "run_id": target_run_id,
                            "message": f"Subscribed to run {target_run_id}"
                        },
                        websocket
                    )

            elif message_type == "unsubscribe":
                # Unsubscribe from a pipeline run
                target_run_id = data.get("run_id")
                if target_run_id:
                    connection_manager.unsubscribe_from_run(websocket, target_run_id)
                    await connection_manager.send_personal_message(
                        {
                            "type": "unsubscribed",
                            "run_id": target_run_id,
                            "message": f"Unsubscribed from run {target_run_id}"
                        },
                        websocket
                    )

            elif message_type == "ping":
                # Respond to ping
                await connection_manager.send_personal_message(
                    {
                        "type": "pong",
                        "timestamp": data.get("timestamp")
                    },
                    websocket
                )

            elif message_type == "get_stats":
                # Send connection statistics
                stats = connection_manager.get_stats()
                await connection_manager.send_personal_message(
                    {
                        "type": "stats",
                        "data": stats
                    },
                    websocket
                )

            else:
                # Unknown message type
                await connection_manager.send_personal_message(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    },
                    websocket
                )

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        # Cancel heartbeat task
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        # Clean up connection
        connection_manager.disconnect(websocket)


@router.get("/ws/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.

    Returns:
        Statistics about active connections and subscriptions
    """
    return connection_manager.get_stats()


@router.get("/ws/health")
async def websocket_health():
    """
    WebSocket health check endpoint.

    Returns:
        Health status and connection count
    """
    return {
        "status": "healthy",
        "active_connections": connection_manager.get_connection_count(),
        "active_runs": len(connection_manager.run_subscriptions)
    }
