"""
WebSocket Package

Real-time updates for pipeline execution via WebSockets.
"""

from .connection_manager import ConnectionManager
from .pipeline_events import PipelineEventEmitter, PipelineEvent, EventType

__all__ = [
    "ConnectionManager",
    "PipelineEventEmitter",
    "PipelineEvent",
    "EventType"
]
