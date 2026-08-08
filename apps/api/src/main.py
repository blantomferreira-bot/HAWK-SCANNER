from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.config.logging import configure_logging
from src.config.settings import get_settings
from src.infrastructure.cache import cache
from src.infrastructure.database import SessionLocal, close_database
from src.presentation.api.v1.router import api_router
from src.presentation.middleware import RateLimitMiddleware, RequestLoggingMiddleware

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await cache.close()
    await close_database()


app = FastAPI(
    title="HAWK SCANNER API",
    summary="Quantitative crypto market intelligence from public data.",
    description="Versioned REST API for rankings, scores, alerts and market intelligence.",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["Health"])
@app.get("/health/live", tags=["Health"])
async def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "hawk-scanner-api", "version": app.version}


@app.get("/health/ready", tags=["Health"])
async def health_ready() -> dict[str, str]:
    """Readiness fails closed when either stateful dependency is unavailable."""
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        await (await cache.client()).ping()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stateful dependencies are unavailable",
        ) from error
    return {"status": "ready", "service": "hawk-scanner-api", "version": app.version}
