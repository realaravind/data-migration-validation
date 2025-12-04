"""
Unit tests for error handler middleware.
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, ValidationError as PydanticValidationError

from errors import (
    OmbudsmanException,
    PipelineNotFoundError,
    InvalidPipelineConfigError,
    register_error_handlers,
    ombudsman_exception_handler,
    validation_error_handler,
    http_exception_handler,
    general_exception_handler,
)


class TestErrorHandlerRegistration:
    """Test error handler registration."""

    def test_register_error_handlers(self):
        """Test that error handlers are registered correctly."""
        app = FastAPI()
        register_error_handlers(app)

        # Check that handlers are registered
        assert len(app.exception_handlers) > 0


class TestOmbudsmanExceptionHandler:
    """Test ombudsman exception handler."""

    @pytest.mark.asyncio
    async def test_pipeline_not_found_handler(self):
        """Test handling of PipelineNotFoundError."""
        # Create a mock request
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            raise PipelineNotFoundError("run_123")

        # Create request object
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # Register handlers
        register_error_handlers(app)

        # Make request
        response = client.get("/test")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PIPELINE_NOT_FOUND"
        assert "run_123" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_invalid_pipeline_config_handler(self):
        """Test handling of InvalidPipelineConfigError."""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            raise InvalidPipelineConfigError(
                message="Missing steps field",
                details={"pipeline": "test"}
            )

        from fastapi.testclient import TestClient
        client = TestClient(app)
        register_error_handlers(app)

        response = client.get("/test")

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_PIPELINE_CONFIG"
        assert response.json()["error"]["details"]["pipeline"] == "test"


class TestValidationErrorHandler:
    """Test Pydantic validation error handler."""

    @pytest.mark.asyncio
    async def test_pydantic_validation_error(self):
        """Test handling of Pydantic validation errors."""
        app = FastAPI()

        class TestModel(BaseModel):
            name: str
            age: int

        @app.post("/test")
        async def test_route(data: TestModel):
            return {"ok": True}

        from fastapi.testclient import TestClient
        client = TestClient(app)
        register_error_handlers(app)

        # Send invalid data (age as string)
        response = client.post("/test", json={"name": "John", "age": "invalid"})

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "validation_errors" in data["error"]["details"]


class TestHTTPExceptionHandler:
    """Test HTTP exception handler."""

    @pytest.mark.asyncio
    async def test_http_404_handler(self):
        """Test handling of 404 HTTP exceptions."""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            raise StarletteHTTPException(status_code=404, detail="Not found")

        from fastapi.testclient import TestClient
        client = TestClient(app)
        register_error_handlers(app)

        response = client.get("/test")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "HTTP_404"
        assert response.json()["error"]["message"] == "Not found"


class TestGeneralExceptionHandler:
    """Test general exception handler."""

    @pytest.mark.asyncio
    async def test_unhandled_exception(self):
        """Test handling of unhandled exceptions."""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            raise ValueError("Something went wrong")

        from fastapi.testclient import TestClient
        client = TestClient(app)
        register_error_handlers(app)

        response = client.get("/test")

        assert response.status_code == 500
        assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "unexpected error" in response.json()["error"]["message"].lower()


class TestErrorResponseFormat:
    """Test that all error responses follow the standard format."""

    @pytest.mark.asyncio
    async def test_error_response_structure(self):
        """Test that error responses have the correct structure."""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            raise PipelineNotFoundError("run_123")

        from fastapi.testclient import TestClient
        client = TestClient(app)
        register_error_handlers(app)

        response = client.get("/test")
        data = response.json()

        # Check structure
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "details" in data["error"]

        # Check types
        assert isinstance(data["error"]["code"], str)
        assert isinstance(data["error"]["message"], str)
        assert isinstance(data["error"]["details"], dict)
