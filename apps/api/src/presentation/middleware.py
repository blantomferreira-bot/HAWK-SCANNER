import hashlib
import time
import uuid

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import get_settings
from src.infrastructure.cache import cache

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed", request_id=request_id, path=request.url.path)
            raise
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window per-client rate limiting stored in Redis."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.url.path in {"/health", "/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)
        settings = get_settings()
        client_ip = request.client.host if request.client else "unknown"
        window = int(time.time() // 60)
        fingerprint = hashlib.sha256(client_ip.encode()).hexdigest()[:24]
        key = f"rate-limit:{window}:{fingerprint}"
        count = await cache.increment(key, ttl_seconds=65)
        if count is not None and count > settings.api_rate_limit_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again in one minute."},
                headers={"Retry-After": "60"},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.api_rate_limit_per_minute)
        return response
