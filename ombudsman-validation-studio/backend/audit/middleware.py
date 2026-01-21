"""
Audit Middleware

FastAPI middleware for automatically logging all API requests.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from .audit_logger import audit_logger


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log all API requests and responses.

    Captures:
    - Request method and path
    - Response status code
    - Request duration
    - User information (if authenticated)
    - Client IP and user agent
    """

    def __init__(self, app: ASGIApp, excluded_paths: list = None):
        """
        Initialize audit middleware.

        Args:
            app: ASGI application
            excluded_paths: List of paths to exclude from audit logging
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process each request and log audit information"""

        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)

        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timer
        start_time = time.time()

        # Extract user information (if available)
        user_id = None
        username = None
        try:
            if hasattr(request.state, "user"):
                user = request.state.user
                user_id = getattr(user, "id", None)
                username = getattr(user, "username", None)
        except:
            pass

        # Extract client information
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Extract query parameters for context
        query_params = dict(request.query_params) if request.query_params else None

        # Log the API request
        audit_logger.log_api_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            username=username,
            ip_address=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            details={
                "query_params": query_params,
                "path_params": request.path_params if request.path_params else None
            }
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
