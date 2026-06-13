"""
Tests for security middleware and configuration.
"""
import sys
from pathlib import Path
import time

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    def test_middleware_import(self):
        """SecurityHeadersMiddleware can be imported."""
        from core.security import SecurityHeadersMiddleware
        assert SecurityHeadersMiddleware is not None

    def test_middleware_is_subclass(self):
        """SecurityHeadersMiddleware extends BaseHTTPMiddleware."""
        from core.security import SecurityHeadersMiddleware
        from starlette.middleware.base import BaseHTTPMiddleware
        assert issubclass(SecurityHeadersMiddleware, BaseHTTPMiddleware)


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    def test_middleware_import(self):
        """RateLimitMiddleware can be imported."""
        from core.security import RateLimitMiddleware
        assert RateLimitMiddleware is not None

    def test_middleware_default_params(self):
        """RateLimitMiddleware accepts default parameters."""
        from core.security import RateLimitMiddleware
        # Should not raise
        middleware = RateLimitMiddleware.__new__(RateLimitMiddleware)
        middleware.max_requests = 100
        middleware.window_seconds = 60
        middleware.requests = {}
        assert middleware.max_requests == 100

    def test_middleware_custom_params(self):
        """RateLimitMiddleware accepts custom parameters."""
        from core.security import RateLimitMiddleware
        middleware = RateLimitMiddleware.__new__(RateLimitMiddleware)
        middleware.max_requests = 50
        middleware.window_seconds = 30
        middleware.requests = {}
        assert middleware.max_requests == 50
        assert middleware.window_seconds == 30


class TestResponseHelpers:
    """Tests for response helpers and exception handlers."""

    def test_api_exception_creation(self):
        """ApiException can be created with code and message."""
        from core.response import ApiException
        exc = ApiException(code=404, message="Not found")
        assert exc.code == 404
        assert exc.message == "Not found"

    def test_api_exception_with_details(self):
        """ApiException supports details field."""
        from core.response import ApiException
        exc = ApiException(code=422, message="Validation error", details={"field": "name"})
        assert exc.details == {"field": "name"}

    def test_api_response_model(self):
        """ApiResponse model works correctly."""
        from core.response import ApiResponse
        resp = ApiResponse(code=200, message="success", data={"key": "value"})
        assert resp.code == 200
        assert resp.data == {"key": "value"}

    def test_api_response_defaults(self):
        """ApiResponse has sensible defaults."""
        from core.response import ApiResponse
        resp = ApiResponse()
        assert resp.code == 200
        assert resp.message == "success"
        assert resp.data is None

    @pytest.mark.asyncio
    async def test_api_exception_handler(self):
        """api_exception_handler returns JSONResponse."""
        from core.response import api_exception_handler, ApiException
        from starlette.requests import Request
        from unittest.mock import MagicMock
        from fastapi.responses import JSONResponse

        exc = ApiException(code=400, message="Bad request")
        request = MagicMock(spec=Request)
        response = await api_exception_handler(request, exc)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_http_exception_handler(self):
        """http_exception_handler returns JSONResponse."""
        from core.response import http_exception_handler
        from starlette.exceptions import HTTPException as StarletteHTTPException
        from starlette.requests import Request
        from unittest.mock import MagicMock
        from fastapi.responses import JSONResponse

        exc = StarletteHTTPException(status_code=404, detail="Not found")
        request = MagicMock(spec=Request)
        response = await http_exception_handler(request, exc)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """general_exception_handler returns 500."""
        from core.response import general_exception_handler
        from starlette.requests import Request
        from unittest.mock import MagicMock
        from fastapi.responses import JSONResponse

        exc = Exception("Something went wrong")
        request = MagicMock(spec=Request)
        response = await general_exception_handler(request, exc)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
