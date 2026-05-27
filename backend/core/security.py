"""
安全中间件
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Optional, Set
import time
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全响应头中间件"""
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单限流中间件"""
    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        max_burst: int = 20,
        burst_window: int = 5,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict = {}

    async def dispatch(self, request, call_next):
        client = request.client.host if request.client else "unknown"
        now = time.time()

        if client not in self.requests:
            self.requests[client] = []

        self.requests[client] = [
            t for t in self.requests[client] if now - t < self.window_seconds
        ]

        if len(self.requests[client]) >= self.max_requests:
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": str(self.window_seconds)}
            )

        self.requests[client].append(now)
        return await call_next(request)
