"""
FastAPI Error Handlers for Ombudsman Validation Studio

This module provides centralized error handling middleware for all API endpoints.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
from typing import Union

from .exceptions import OmbudsmanException

logger = logging.getLogger(__name__)


async def ombudsman_exception_handler(request: Request, exc: OmbudsmanException) -> JSONResponse:
    """
    Handler for all custom Ombudsman exceptions.

    Returns structured error response with appropriate status code.
    """
    # Log the error with context
    logger.error(
        f"OmbudsmanException: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler for Pydantic validation errors (invalid request data).

    Converts Pydantic validation errors to our standard error format.
    """
    # Extract validation errors
    errors = exc.errors()

    # Format errors for better readability
    formatted_errors = []
    for error in errors:
        location = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append({
            "field": location,
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        f"Request validation failed: {len(formatted_errors)} errors",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": formatted_errors
        }
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {
                    "validation_errors": formatted_errors
                }
            }
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handler for standard HTTP exceptions.

    Converts Starlette HTTP exceptions to our standard error format.
    """
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": {}
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for all unhandled exceptions.

    Logs full traceback and returns generic error response to avoid leaking internals.
    """
    # Log full traceback for debugging
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
        },
        exc_info=True  # Include full traceback
    )

    # Print traceback for immediate visibility during development
    traceback.print_exc()

    # Return generic error to client (don't leak internals)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please contact support.",
                "details": {
                    "exception_type": type(exc).__name__,
                    # Include exception message in development mode only
                    # "exception_message": str(exc)  # Uncomment for development
                }
            }
        }
    )


def register_error_handlers(app):
    """
    Register all error handlers with the FastAPI application.

    Usage:
        from errors.handlers import register_error_handlers

        app = FastAPI()
        register_error_handlers(app)
    """
    # Custom Ombudsman exceptions
    app.add_exception_handler(OmbudsmanException, ombudsman_exception_handler)

    # Request validation errors
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    # HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Catch-all for unhandled exceptions
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Error handlers registered successfully")
