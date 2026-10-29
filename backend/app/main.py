import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api import downloads, health, info
from app.config import settings
from app.core.errors import AppError
from app.core.rate_limit import limiter
from app.services.cleanup import cleanup_loop
from app.services.job_manager import manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    await manager.cleanup_orphans()
    cleanup_task = asyncio.create_task(
        cleanup_loop(
            manager,
            settings.file_ttl_minutes,
            settings.cleanup_interval_seconds,
        ),
        name="ytd-cleanup",
    )
    logger.info(
        "YTD started (downloads=%s, ttl=%s min, max concurrent=%s)",
        settings.download_dir,
        settings.file_ttl_minutes,
        settings.max_concurrent_jobs,
    )
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        await manager.shutdown()
        logger.info("YTD stopped")


app = FastAPI(
    title="YTD API",
    description="YouTube downloader backend built on FastAPI and yt-dlp.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.info("%s %s -> %s: %s", request.method, request.url.path, exc.code, exc.message)
    headers = {"Retry-After": "60"} if exc.code == "RATE_LIMITED" else None
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    url_error = any("url" in [str(part) for part in error.get("loc", ())] for error in errors)
    if url_error:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_URL",
                    "message": "Please enter a valid YouTube URL.",
                }
            },
        )
    logger.info("Validation error on %s: %s", request.url.path, errors)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INTERNAL",
                "message": "Invalid request.",
            }
        },
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    logger.info("Rate limit hit by %s on %s", request.client, request.url.path)
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too many requests. Please wait a moment and try again.",
            }
        },
        headers={"Retry-After": "60"},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL",
                "message": "Something went wrong. Please try again.",
            }
        },
    )


app.include_router(health.router, prefix="/api")
app.include_router(info.router, prefix="/api")
app.include_router(downloads.router, prefix="/api")
