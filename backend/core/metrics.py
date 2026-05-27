"""
Prometheus指标
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"]
)

active_scans = Gauge(
    "pmrs_active_scans",
    "Number of active vulnerability scans"
)

vulnerabilities_found = Counter(
    "pmrs_vulnerabilities_found_total",
    "Total vulnerabilities found",
    ["protocol", "severity"]
)

crashes_detected = Counter(
    "pmrs_crashes_detected_total",
    "Total crashes detected during fuzzing",
    ["protocol"]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """指标收集中间件"""
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response


async def metrics_endpoint(request: Request):
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Alias for main.py compatibility
metrics = metrics_endpoint
