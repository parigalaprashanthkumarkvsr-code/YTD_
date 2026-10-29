import asyncio
import json
import logging
import shutil
import threading
import uuid
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import settings
from app.core.errors import (
    AppError,
    DownloadCancelledError,
    FileNotReadyError,
    NotFoundError,
)
from app.core.files import sanitize_filename
from app.core.validators import parse_youtube_url
from app.schemas import JobState, PlaylistProgress
from app.services.ytdlp_service import (
    PlaylistProgressCallback,
    ProgressCallback,
    run_download,
    run_playlist_download,
)

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = frozenset({"done", "error", "cancelled"})


@dataclass
class Job:
    id: str
    url: str
    kind: str
    format_id: str | None
    audio_format: str
    is_playlist: bool
    max_height: int | None
    video_ids: list[str] | None
    directory: Path
    created_at: datetime
    status: str = "queued"
    percent: float = 0.0
    speed: str | None = None
    eta: int | None = None
    filename: str | None = None
    error: str | None = None
    playlist: PlaylistProgress | None = None
    finished_at: datetime | None = None
    started: bool = False
    cancel_event: threading.Event = field(default_factory=threading.Event)
    subscribers: set[asyncio.Queue[dict[str, object]]] = field(default_factory=set)
    task: asyncio.Task[None] | None = None

    def snapshot(self) -> JobState:
        return JobState(
            id=self.id,
            status=self.status,  # type: ignore[arg-type]
            percent=round(self.percent, 1),
            speed=self.speed,
            eta=self.eta,
            filename=self.filename,
            error=self.error,
            created_at=self.created_at,
            playlist=self.playlist,
        )


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def require(self, job_id: str) -> Job:
        job = self.get(job_id)
        if job is None:
            raise NotFoundError()
        return job

    async def create(
        self,
        *,
        url: str,
        kind: str,
        format_id: str | None,
        audio_format: str,
        max_height: int | None = None,
        video_ids: list[str] | None = None,
    ) -> JobState:
        target = parse_youtube_url(url)
        job_id = uuid.uuid4().hex
        job_dir = settings.download_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        job = Job(
            id=job_id,
            url=url,
            kind=kind,
            format_id=format_id,
            audio_format=audio_format,
            is_playlist=target.kind == "playlist",
            max_height=max_height,
            video_ids=video_ids,
            directory=job_dir,
            created_at=datetime.now(UTC),
        )
        self._jobs[job_id] = job
        job.task = asyncio.create_task(self._run(job), name=f"ytd-{job_id}")
        return job.snapshot()

    async def _run(self, job: Job) -> None:
        acquired = False
        try:
            if job.status == "cancelled":
                return
            await self._semaphore.acquire()
            acquired = True
            job.started = True
            if job.status == "cancelled":
                return

            self._update(job, status="downloading", percent=0.0, speed=None, eta=None)

            loop = asyncio.get_running_loop()

            def schedule_progress(
                percent: float,
                speed: str | None,
                eta: int | None,
                status: str,
                playlist: PlaylistProgress | None = None,
            ) -> None:
                if job.status == "cancelled":
                    return
                try:
                    loop.call_soon_threadsafe(
                        self._apply_progress,
                        job,
                        percent,
                        speed,
                        eta,
                        status,
                        playlist,
                    )
                except RuntimeError:
                    logger.debug("Progress callback dropped after event loop closed")

            def progress_callback(
                percent: float,
                speed: str | None,
                eta: int | None,
                status: str,
            ) -> None:
                schedule_progress(percent, speed, eta, status)

            def playlist_progress_callback(
                percent: float,
                speed: str | None,
                eta: int | None,
                status: str,
                current_item: int,
                total_items: int,
                current_title: str,
                skipped_items: int,
            ) -> None:
                schedule_progress(
                    percent,
                    speed,
                    eta,
                    status,
                    PlaylistProgress(
                        total_items=total_items,
                        completed_items=min(current_item - 1, total_items),
                        current_item=current_item,
                        current_title=current_title or None,
                        skipped_items=skipped_items,
                    ),
                )

            progress: ProgressCallback = progress_callback
            playlist_progress: PlaylistProgressCallback = playlist_progress_callback

            if job.is_playlist:
                output = await asyncio.to_thread(
                    run_playlist_download,
                    url=job.url,
                    kind=job.kind,
                    audio_format=job.audio_format,
                    max_height=job.max_height,
                    job_dir=job.directory,
                    progress=playlist_progress,
                    cancel_event=job.cancel_event,
                    video_ids=job.video_ids,
                )
            else:
                output = await asyncio.to_thread(
                    run_download,
                    url=job.url,
                    kind=job.kind,
                    format_id=job.format_id,
                    audio_format=job.audio_format,
                    job_dir=job.directory,
                    progress=progress,
                    cancel_event=job.cancel_event,
                )

            # Progress callbacks are scheduled from the worker thread. Yield once
            # so queued updates are applied before the terminal snapshot.
            await asyncio.sleep(0)

            if job.status == "cancelled":
                return

            filename = sanitize_filename(output.name)
            if output.name != filename:
                target = output.with_name(filename)
                output.replace(target)
                output = target

            changes: dict[str, object] = {
                "status": "done",
                "percent": 100.0,
                "speed": None,
                "eta": None,
                "filename": filename,
                "error": None,
            }
            if job.is_playlist and job.playlist is not None:
                changes["playlist"] = job.playlist.model_copy(
                    update={
                        "completed_items": job.playlist.total_items,
                        "current_item": job.playlist.total_items,
                        "current_title": None,
                    }
                )
            self._update(job, **changes)
            logger.info("Job %s finished: %s", job.id, filename)
        except DownloadCancelledError:
            self._mark_cancelled(job)
        except AppError as exc:
            if job.status != "cancelled":
                logger.warning("Job %s failed: %s", job.id, exc.message)
                self._update(job, status="error", speed=None, eta=None, error=exc.message)
        except Exception:
            if job.status != "cancelled":
                logger.exception("Job %s failed unexpectedly", job.id)
                self._update(
                    job,
                    status="error",
                    speed=None,
                    eta=None,
                    error="Download failed. Please try again.",
                )
        finally:
            if acquired:
                self._semaphore.release()
            if job.finished_at is None:
                job.finished_at = datetime.now(UTC)
            if job.status in {"error", "cancelled"}:
                self._delete_files(job)

    def _apply_progress(
        self,
        job: Job,
        percent: float,
        speed: str | None,
        eta: int | None,
        status: str,
        playlist: PlaylistProgress | None = None,
    ) -> None:
        if job.status == "cancelled" or job.status in TERMINAL_STATUSES:
            return
        if status not in {"downloading", "processing"}:
            return
        changes: dict[str, object] = {
            "status": status,
            "percent": percent,
            "speed": speed,
            "eta": eta,
        }
        if playlist is not None:
            changes["playlist"] = playlist
        self._update(job, **changes)

    def _update(self, job: Job, **changes: object) -> None:
        if job.status == "cancelled" and changes.get("status") != "cancelled":
            return
        if job.status in TERMINAL_STATUSES and changes.get("status") not in TERMINAL_STATUSES:
            return

        for key, value in changes.items():
            setattr(job, key, value)

        if job.status in TERMINAL_STATUSES and job.finished_at is None:
            job.finished_at = datetime.now(UTC)

        self._publish(job)

    def _publish(self, job: Job) -> None:
        payload = job.snapshot().model_dump(mode="json")
        for queue in list(job.subscribers):
            if queue.full():
                with suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.debug("Dropped progress event for job %s", job.id)

    async def event_stream(self, job_id: str) -> AsyncIterator[str]:
        job = self.require(job_id)
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=128)
        job.subscribers.add(queue)
        try:
            yield self._sse(job.snapshot().model_dump(mode="json"))
            if job.status in TERMINAL_STATUSES:
                return

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue

                yield self._sse(event)
                if event.get("status") in TERMINAL_STATUSES:
                    return
        finally:
            job.subscribers.discard(queue)

    @staticmethod
    def _sse(payload: dict[str, object]) -> str:
        return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"

    async def cancel(self, job_id: str) -> None:
        job = self.require(job_id)

        if job.status in TERMINAL_STATUSES:
            self._delete_files(job)
            self._jobs.pop(job_id, None)
            return

        job.cancel_event.set()
        self._mark_cancelled(job)
        if not job.started:
            self._delete_files(job)
        logger.info("Job %s cancelled", job.id)

    def _mark_cancelled(self, job: Job) -> None:
        if job.status == "cancelled":
            return
        self._update(
            job,
            status="cancelled",
            speed=None,
            eta=None,
            error="Download cancelled.",
        )

    def file_path(self, job_id: str) -> Path:
        job = self.require(job_id)
        if job.status != "done" or not job.filename:
            raise FileNotReadyError()
        path = (job.directory / job.filename).resolve()
        if job.directory.resolve() not in path.parents or not path.is_file():
            raise FileNotReadyError("The file is no longer available. It may have expired.")
        return path

    async def cleanup_expired(self, ttl_minutes: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(minutes=ttl_minutes)
        expired: list[Job] = []
        for job in list(self._jobs.values()):
            finished = job.finished_at or job.created_at
            if job.status in TERMINAL_STATUSES and finished < cutoff:
                expired.append(job)

        for job in expired:
            self._delete_files(job)
            self._jobs.pop(job.id, None)

        if expired:
            logger.info("Cleaned up %d expired job(s)", len(expired))
        return len(expired)

    async def cleanup_orphans(self) -> int:
        settings.download_dir.mkdir(parents=True, exist_ok=True)
        removed = 0
        for child in settings.download_dir.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                removed += 1
            except OSError:
                logger.exception("Could not remove orphaned path %s", child)
        if removed:
            logger.info("Removed %d orphaned download path(s)", removed)
        return removed

    async def shutdown(self) -> None:
        tasks: list[asyncio.Task[None]] = []
        for job in self._jobs.values():
            if job.status not in TERMINAL_STATUSES:
                job.cancel_event.set()
                if job.task and not job.task.done():
                    tasks.append(job.task)
        if not tasks:
            return
        done, pending = await asyncio.wait(tasks, timeout=5)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        logger.info("Stopped %d active download task(s)", len(done) + len(pending))

    @staticmethod
    def _delete_files(job: Job) -> None:
        try:
            if job.directory.exists():
                shutil.rmtree(job.directory, ignore_errors=True)
        except OSError:
            logger.exception("Could not delete files for job %s", job.id)


manager = JobManager()


__all__ = ["Job", "JobManager", "manager"]
