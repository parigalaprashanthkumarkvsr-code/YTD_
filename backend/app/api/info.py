from fastapi import APIRouter, Request

from app.config import settings
from app.core.rate_limit import limiter
from app.schemas import InfoRequest, MediaInfoResponse
from app.services.ytdlp_service import get_media_info

router = APIRouter(tags=["metadata"])


@router.post("/info", response_model=MediaInfoResponse)
@limiter.limit(settings.rate_limit)
async def media_info(request: Request, body: InfoRequest) -> MediaInfoResponse:
    """Fetch metadata and available formats for a YouTube video or playlist."""
    return await get_media_info(str(body.url))
