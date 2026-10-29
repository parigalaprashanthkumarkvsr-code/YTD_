from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from app.config import settings
from app.core.rate_limit import limiter
from app.schemas import DownloadAccepted, DownloadRequest, JobState
from app.services.job_manager import Job, manager

router = APIRouter(prefix="/downloads", tags=["downloads"])


@router.post("", response_model=DownloadAccepted, status_code=202)
@limiter.limit(settings.rate_limit)
async def create_download(request: Request, body: DownloadRequest) -> DownloadAccepted:
    """Queue a download job and return its id."""
    state = await manager.create(
        url=str(body.url),
        kind=body.kind,
        format_id=body.format_id,
        audio_format=body.audio_format,
        max_height=body.max_height,
    )
    return DownloadAccepted(job_id=state.id)


@router.get("/{job_id}", response_model=JobState)
async def get_download(job_id: str) -> JobState:
    """Return a point-in-time snapshot of a job."""
    return manager.require(job_id).snapshot()


@router.get("/{job_id}/events")
async def download_events(job_id: str) -> StreamingResponse:
    """Stream job progress as Server-Sent Events until the job is terminal."""
    manager.require(job_id)
    return StreamingResponse(
        manager.event_stream(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/file")
async def download_file(job_id: str) -> FileResponse:
    """Serve the finished file for a completed job."""
    job: Job = manager.require(job_id)
    path = manager.file_path(job_id)
    return FileResponse(
        path,
        filename=job.filename or path.name,
        media_type="application/octet-stream",
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/{job_id}", status_code=204)
async def cancel_download(job_id: str) -> Response:
    """Cancel an active job, or clean up a finished one."""
    await manager.cancel(job_id)
    return Response(status_code=204)
