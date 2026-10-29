import shutil

from fastapi import APIRouter
from yt_dlp.version import __version__ as yt_dlp_version

from app.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    has_ffmpeg = shutil.which("ffmpeg") is not None
    return HealthResponse(
        status="ok" if has_ffmpeg else "degraded",
        yt_dlp_version=yt_dlp_version,
        ffmpeg=has_ffmpeg,
    )
