import asyncio
import logging
import shutil
import threading
import time
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import yt_dlp
from yt_dlp.utils import DownloadError

from app.config import settings
from app.core.errors import (
    AgeRestrictedError,
    AppError,
    DownloadCancelledError,
    RegionBlockedError,
    TooLongError,
    VideoInfoError,
    VideoUnavailableError,
)
from app.core.files import sanitize_filename
from app.core.validators import VIDEO_ID_RE, parse_youtube_url
from app.schemas import FormatOption, PlaylistInfoResponse, PlaylistItem, VideoInfoResponse

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str | None, int | None, str], None]
PlaylistProgressCallback = Callable[
    [float, str | None, int | None, str, int, int, str, int],
    None,
]

_IGNORED_SUFFIXES = {
    ".part",
    ".ytdl",
    ".temp",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".vtt",
    ".srt",
    ".ass",
    ".json",
}


class _YtdlpLogger:
    def debug(self, message: str) -> None:
        logger.debug("yt-dlp: %s", message)

    def info(self, message: str) -> None:
        logger.debug("yt-dlp: %s", message)

    def warning(self, message: str) -> None:
        logger.warning("yt-dlp: %s", message)

    def error(self, message: str) -> None:
        logger.error("yt-dlp: %s", message)


def _base_options() -> dict[str, Any]:
    return {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "cachedir": False,
        "socket_timeout": 20,
        "retries": 3,
        "extractor_retries": 2,
        "logger": _YtdlpLogger(),
    }


def _classify_error(exc: Exception) -> AppError:
    message = str(exc).lower()

    if any(
        term in message
        for term in (
            "age-restricted",
            "age restricted",
            "confirm your age",
            "age verification",
            "inappropriate for some users",
        )
    ):
        return AgeRestrictedError()
    if any(term in message for term in ("region", "country", "geo restrict", "geo-restrict")):
        return RegionBlockedError()
    if "max-filesize" in message or "larger than" in message or "file is too large" in message:
        return TooLongError(f"The file exceeds the {settings.max_filesize_mb} MB size limit.")
    if "too long" in message or "duration" in message:
        return TooLongError()
    if any(
        term in message
        for term in (
            "private",
            "unavailable",
            "removed",
            "does not exist",
            "members-only",
            "not available",
            "live event",
            "is live",
        )
    ):
        return VideoUnavailableError()
    if "sign in" in message or "not a bot" in message or "confirm you" in message:
        return VideoUnavailableError(
            "YouTube rejected the request. Please try again in a moment or update yt-dlp."
        )
    return VideoInfoError()


@dataclass(frozen=True)
class _PlaylistPayload:
    id: str
    title: str
    channel: str
    duration: int
    thumbnail: str | None
    entries: list[dict[str, Any]]


def _thumbnail_of(entry: dict[str, Any]) -> str | None:
    thumbnail = entry.get("thumbnail")
    if thumbnail:
        return str(thumbnail)
    thumbnails = entry.get("thumbnails") or []
    for candidate in reversed(thumbnails):
        if candidate.get("url"):
            return str(candidate["url"])
    return None


def _extract_playlist_payload_sync(url: str) -> _PlaylistPayload:
    target = parse_youtube_url(url)
    if target.kind != "playlist":
        raise VideoInfoError("This link is not a playlist.")

    options = _base_options()
    options.update(
        {
            "noplaylist": False,
            "skip_download": True,
            "extract_flat": "in_playlist",
            # Fetch one extra entry so an oversized playlist can be rejected
            # without paging through the entire list.
            "playlistend": settings.max_playlist_items + 1,
        }
    )

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as exc:
        logger.warning("Playlist extraction failed for %s: %s", url, exc)
        error = _classify_error(exc)
        if isinstance(error, VideoUnavailableError):
            raise VideoUnavailableError(
                "This playlist is unavailable. It may be private, removed, or empty."
            ) from exc
        raise error from exc
    except Exception as exc:
        logger.exception("Unexpected playlist metadata error for %s", url)
        raise VideoInfoError("Could not fetch playlist details. Please try again.") from exc

    if not info:
        raise VideoUnavailableError("This playlist is unavailable.")

    raw_entries = list(info.get("entries") or [])
    if not raw_entries:
        raise VideoUnavailableError("This playlist is empty or unavailable.")
    if len(raw_entries) > settings.max_playlist_items:
        raise TooLongError(
            f"This playlist has more than {settings.max_playlist_items} videos. "
            "Choose a shorter playlist."
        )

    entries = []
    for entry in raw_entries:
        if not entry:
            continue
        video_id = str(entry.get("id") or "")
        if VIDEO_ID_RE.fullmatch(video_id):
            entries.append(entry)

    if not entries:
        raise VideoUnavailableError("No downloadable videos were found in this playlist.")

    thumbnail = _thumbnail_of(info) or _thumbnail_of(entries[0])
    duration = sum(int(entry.get("duration") or 0) for entry in entries)

    return _PlaylistPayload(
        id=str(info.get("id") or target.id),
        title=str(info.get("title") or "YouTube playlist"),
        channel=str(info.get("channel") or info.get("uploader") or "Unknown channel"),
        duration=duration,
        thumbnail=thumbnail,
        entries=entries,
    )


def _extract_playlist_info_sync(url: str) -> PlaylistInfoResponse:
    payload = _extract_playlist_payload_sync(url)
    items = [
        PlaylistItem(
            id=str(entry["id"]),
            title=str(entry.get("title") or f"Video {index}"),
            duration=int(entry.get("duration") or 0),
            thumbnail=_thumbnail_of(entry),
        )
        for index, entry in enumerate(payload.entries, start=1)
    ]
    return PlaylistInfoResponse(
        id=payload.id,
        title=payload.title,
        channel=payload.channel,
        video_count=len(items),
        duration=payload.duration,
        thumbnail=payload.thumbnail,
        items=items,
    )


def _extract_info_sync(url: str) -> VideoInfoResponse:
    options = _base_options()
    options["skip_download"] = True

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as exc:
        logger.warning("Metadata extraction failed for %s: %s", url, exc)
        raise _classify_error(exc) from exc
    except Exception as exc:
        logger.exception("Unexpected metadata error for %s", url)
        raise VideoInfoError() from exc

    if not info:
        raise VideoUnavailableError()

    if info.get("entries"):
        entries = [entry for entry in info["entries"] if entry]
        if not entries:
            raise VideoUnavailableError()
        info = entries[0]

    if info.get("is_live"):
        raise VideoUnavailableError("Live streams cannot be downloaded.")

    duration = int(info.get("duration") or 0)
    if duration > settings.max_duration_seconds:
        limit_hours = settings.max_duration_seconds / 3600
        raise TooLongError(f"This video is longer than the {limit_hours:g} hour limit.")

    formats = _build_formats(info)
    if not formats:
        raise VideoUnavailableError("No downloadable formats were found for this video.")

    thumbnail = info.get("thumbnail")
    if not thumbnail:
        thumbnails = info.get("thumbnails") or []
        if thumbnails:
            thumbnail = thumbnails[-1].get("url")

    video_id = str(info.get("id") or _id_from_url(url))

    return VideoInfoResponse(
        id=video_id,
        title=str(info.get("title") or "Untitled video"),
        channel=str(info.get("channel") or info.get("uploader") or "Unknown channel"),
        duration=duration,
        thumbnail=str(thumbnail) if thumbnail else None,
        formats=formats,
    )


def _id_from_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")
    return parse_qs(parsed.query).get("v", ["unknown"])[0]


def _size_of(fmt: dict[str, Any], duration: int = 0) -> int | None:
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    if size:
        return int(size)
    if duration > 0:
        bitrate = fmt.get("tbr") or fmt.get("vbr") or fmt.get("abr")
        if bitrate:
            return int(float(bitrate) * 1000 / 8 * duration)
    return None


def _audio_sort_key(fmt: dict[str, Any]) -> tuple[int, float]:
    codec_preference = 1 if fmt.get("ext") == "m4a" else 0
    return (codec_preference, float(fmt.get("abr") or fmt.get("tbr") or 0))


def _build_formats(info: dict[str, Any]) -> list[FormatOption]:
    duration = int(info.get("duration") or 0)
    raw_formats = [fmt for fmt in info.get("formats") or [] if fmt.get("format_id")]
    audio_formats = [
        fmt
        for fmt in raw_formats
        if fmt.get("acodec") not in (None, "none")
        and fmt.get("vcodec") in (None, "none")
        and not str(fmt.get("format_note") or "").lower().startswith("storyboard")
    ]
    best_audio = max(audio_formats, key=_audio_sort_key, default=None)
    best_m4a = max(
        (fmt for fmt in audio_formats if fmt.get("ext") == "m4a"),
        key=_audio_sort_key,
        default=None,
    )

    video_formats = [
        fmt
        for fmt in raw_formats
        if fmt.get("vcodec") not in (None, "none")
        and isinstance(fmt.get("height"), int)
        and not str(fmt.get("format_note") or "").lower().startswith("storyboard")
    ]

    by_height: dict[int, dict[str, Any]] = {}
    for fmt in video_formats:
        height = int(fmt["height"])
        current = by_height.get(height)
        if current is None or _video_sort_key(fmt) > _video_sort_key(current):
            by_height[height] = fmt

    options: list[FormatOption] = []
    for height in sorted(by_height, reverse=True):
        video = by_height[height]
        video_ext = str(video.get("ext") or "mp4")
        has_audio = video.get("acodec") not in (None, "none")

        if has_audio:
            format_id = str(video["format_id"])
            filesize = _size_of(video, duration)
        else:
            audio = (best_m4a or best_audio) if video_ext == "mp4" else best_audio
            if audio is None:
                continue
            format_id = f"{video['format_id']}+{audio['format_id']}"
            video_size = _size_of(video, duration) or 0
            audio_size = _size_of(audio, duration) or 0
            filesize = (video_size + audio_size) if (video_size and audio_size) else None

        options.append(
            FormatOption(
                format_id=format_id,
                label=f"{height}p {video_ext.upper()}",
                ext=video_ext,
                height=height,
                filesize=filesize,
            )
        )

    if best_audio is not None:
        options.append(
            FormatOption(
                format_id="bestaudio",
                label="Audio only",
                ext=str(best_audio.get("ext") or "m4a"),
                height=None,
                filesize=_size_of(best_audio, duration),
            )
        )

    return options


def _video_sort_key(fmt: dict[str, Any]) -> tuple[int, int, float]:
    # Prefer MP4 (mergeable into MP4), then a video-only stream (higher quality),
    # then the highest bitrate.
    mp4 = 1 if fmt.get("ext") == "mp4" else 0
    video_only = 1 if fmt.get("acodec") in (None, "none") else 0
    return (mp4, video_only, float(fmt.get("tbr") or 0))


def extract_video_info(url: str) -> VideoInfoResponse:
    """Extract metadata in a way that callers can await via ``asyncio.to_thread``."""
    return _extract_info_sync(url)


async def get_video_info(url: str) -> VideoInfoResponse:
    return await asyncio.to_thread(_extract_info_sync, url)


def _extract_media_info_sync(url: str) -> VideoInfoResponse | PlaylistInfoResponse:
    if parse_youtube_url(url).kind == "playlist":
        return _extract_playlist_info_sync(url)
    return _extract_info_sync(url)


async def get_media_info(url: str) -> VideoInfoResponse | PlaylistInfoResponse:
    return await asyncio.to_thread(_extract_media_info_sync, url)


def _playlist_format_selector(max_height: int | None) -> str:
    if max_height is None:
        return "bestvideo+bestaudio/best"
    return f"bestvideo[height<={max_height}]+bestaudio/" f"best[height<={max_height}]/best"


def _format_speed(speed: float | None) -> str | None:
    if not speed or speed <= 0:
        return None
    if speed >= 1024 * 1024:
        return f"{speed / (1024 * 1024):.1f}MiB/s"
    if speed >= 1024:
        return f"{speed / 1024:.0f}KiB/s"
    return f"{speed:.0f}B/s"


def _make_progress_hook(
    progress: ProgressCallback,
    cancel_event: threading.Event,
    expected_streams: int,
) -> Callable[[dict[str, Any]], None]:
    last_emit = 0.0
    last_percent = -1.0
    completed_streams = 0
    expected = max(1, expected_streams)

    def hook(data: dict[str, Any]) -> None:
        nonlocal last_emit, last_percent, completed_streams
        if cancel_event.is_set():
            raise DownloadCancelledError

        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            fraction = (downloaded / total) if total else 0.0
            percent = min(99.0, (completed_streams + fraction) / expected * 100)
            now = time.monotonic()
            if percent - last_percent < 0.5 and now - last_emit < 0.4:
                return
            last_emit = now
            last_percent = percent
            eta = data.get("eta")
            progress(
                round(max(0.0, percent), 1),
                _format_speed(data.get("speed")),
                int(eta) if eta is not None else None,
                "downloading",
            )
        elif status == "finished":
            completed_streams = min(expected, completed_streams + 1)
            last_percent = min(99.0, completed_streams / expected * 100)
            progress(last_percent, None, None, "downloading")

    return hook


def _make_postprocessor_hook(
    progress: ProgressCallback,
    cancel_event: threading.Event,
) -> Callable[[dict[str, Any]], None]:
    last_status: str | None = None

    def hook(data: dict[str, Any]) -> None:
        nonlocal last_status
        if cancel_event.is_set():
            raise DownloadCancelledError
        status = str(data.get("status") or "")
        if status != last_status and status in {"started", "processing"}:
            last_status = status
            progress(100.0, None, None, "processing")

    return hook


def run_download(
    *,
    url: str,
    kind: str,
    format_id: str | None,
    audio_format: str,
    job_dir: Path,
    progress: ProgressCallback,
    cancel_event: threading.Event,
) -> Path:
    """Download a video or audio file into ``job_dir`` and return the final path."""
    job_dir.mkdir(parents=True, exist_ok=True)

    options = _base_options()
    expected_streams = 1
    if kind == "video":
        selector = format_id or "bestvideo+bestaudio/best"
        expected_streams = 2 if "+" in selector else 1

    options.update(
        {
            "outtmpl": str(job_dir / "%(title)s [%(id)s].%(ext)s"),
            "overwrites": True,
            "continuedl": False,
            "progress_hooks": [_make_progress_hook(progress, cancel_event, expected_streams)],
            "postprocessor_hooks": [_make_postprocessor_hook(progress, cancel_event)],
            "max_filesize": settings.max_filesize_mb * 1024 * 1024,
        }
    )

    if kind == "audio":
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "192",
            }
        ]
    else:
        options["format"] = format_id or "bestvideo+bestaudio/best"
        options["merge_output_format"] = "mp4/mkv"

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
    except DownloadCancelledError:
        raise
    except DownloadError as exc:
        logger.warning("Download failed for %s: %s", url, exc)
        raise _classify_error(exc) from exc
    except Exception as exc:
        logger.exception("Unexpected download error for %s", url)
        raise VideoInfoError("Download failed. Please try again.") from exc

    if cancel_event.is_set():
        raise DownloadCancelledError

    return _find_output_file(job_dir, kind, audio_format)


def _dedupe_arcname(name: str, used: set[str], fallback: str) -> str:
    safe = sanitize_filename(name, fallback=fallback)
    stem, extension = safe.rsplit(".", 1) if "." in safe else (safe, "")
    candidate = safe
    counter = 2
    while candidate.lower() in used:
        candidate = f"{stem} ({counter}){f'.{extension}' if extension else ''}"
        counter += 1
    used.add(candidate.lower())
    return candidate


def _write_playlist_zip(
    zip_path: Path,
    outputs: list[tuple[Path, str]],
    cancel_event: threading.Event,
) -> None:
    with zipfile.ZipFile(
        zip_path,
        mode="w",
        compression=zipfile.ZIP_STORED,
        allowZip64=True,
    ) as archive:
        for output, arcname in outputs:
            if cancel_event.is_set():
                raise DownloadCancelledError
            with output.open("rb") as source, archive.open(arcname, "w") as target:
                while chunk := source.read(1024 * 1024):
                    if cancel_event.is_set():
                        raise DownloadCancelledError
                    target.write(chunk)


def run_playlist_download(
    *,
    url: str,
    kind: str,
    audio_format: str,
    max_height: int | None,
    job_dir: Path,
    progress: PlaylistProgressCallback,
    cancel_event: threading.Event,
    video_ids: list[str] | None = None,
) -> Path:
    """Download selected videos from a playlist into one ZIP file.

    Individual unavailable, private, or over-limit items are skipped. If no
    items can be downloaded the job fails. Cancellation is checked between
    items and while the archive is being written.
    """
    if cancel_event.is_set():
        raise DownloadCancelledError

    payload = _extract_playlist_payload_sync(url)

    missing = 0
    if video_ids is None:
        entries = payload.entries
    else:
        wanted = set(video_ids)
        entries = [entry for entry in payload.entries if str(entry["id"]) in wanted]
        missing = max(0, len(wanted) - len(entries))
        if missing:
            logger.info("%s selected playlist items are no longer available", missing)

    if not entries:
        message = (
            "None of the selected videos could be found in this playlist."
            if video_ids is not None
            else "No videos in this playlist could be downloaded."
        )
        raise VideoUnavailableError(message)

    total = len(entries) + missing
    items_dir = job_dir / "items"
    items_dir.mkdir(parents=True, exist_ok=True)

    selector = _playlist_format_selector(max_height) if kind == "video" else None
    processed = 0
    skipped = missing
    outputs: list[tuple[Path, str]] = []
    used_names: set[str] = set()

    for index, entry in enumerate(entries, start=1):
        if cancel_event.is_set():
            raise DownloadCancelledError

        video_id = str(entry["id"])
        title = str(entry.get("title") or f"Video {index}")
        duration = int(entry.get("duration") or 0)

        progress(
            round(processed / total * 100, 1),
            None,
            None,
            "downloading",
            index,
            total,
            title,
            skipped,
        )

        if duration > settings.max_duration_seconds:
            logger.info(
                "Skipping playlist item %s (%ss) because it exceeds the duration limit",
                video_id,
                duration,
            )
            skipped += 1
            processed += 1
            continue

        item_dir = items_dir / f"{index:03d}"

        def item_progress(
            percent: float,
            speed: str | None,
            eta: int | None,
            status: str,
            *,
            _index: int = index,
            _title: str = title,
        ) -> None:
            fraction = max(0.0, min(100.0, percent)) / 100
            # These counters intentionally reflect the live loop state.
            overall = min(99.0, ((processed + fraction) / total) * 100)  # noqa: B023
            progress(
                round(overall, 1),
                speed,
                eta,
                status,
                _index,
                total,
                _title,
                skipped,  # noqa: B023
            )

        try:
            output = run_download(
                url=f"https://www.youtube.com/watch?v={video_id}",
                kind=kind,
                format_id=selector,
                audio_format=audio_format,
                job_dir=item_dir,
                progress=item_progress,
                cancel_event=cancel_event,
            )
        except DownloadCancelledError:
            raise
        except AppError as exc:
            logger.warning(
                "Skipping playlist item %s (%s): %s",
                video_id,
                title,
                exc.message,
            )
            shutil.rmtree(item_dir, ignore_errors=True)
            skipped += 1
            processed += 1
            continue

        arcname = _dedupe_arcname(
            output.name,
            used_names,
            fallback=f"video-{index:03d}{output.suffix}",
        )
        outputs.append((output, arcname))
        processed += 1
        progress(
            min(99.0, round(processed / total * 100, 1)),
            None,
            None,
            "downloading",
            index,
            total,
            title,
            skipped,
        )

    if not outputs:
        message = (
            "No videos in this playlist could be downloaded."
            if video_ids is None
            else "None of the selected videos could be downloaded."
        )
        raise VideoUnavailableError(message)

    if cancel_event.is_set():
        raise DownloadCancelledError

    progress(
        99.0,
        None,
        None,
        "processing",
        total,
        total,
        "",
        skipped,
    )

    zip_name = sanitize_filename(f"{payload.title}.zip", fallback="playlist.zip")
    zip_path = job_dir / zip_name
    _write_playlist_zip(zip_path, outputs, cancel_event)
    shutil.rmtree(items_dir, ignore_errors=True)

    if cancel_event.is_set():
        raise DownloadCancelledError

    return zip_path


def _find_output_file(job_dir: Path, kind: str, audio_format: str) -> Path:
    candidates = [
        path
        for path in job_dir.rglob("*")
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() not in _IGNORED_SUFFIXES
    ]

    if kind == "audio":
        preferred = [path for path in candidates if path.suffix.lower() == f".{audio_format}"]
        if preferred:
            candidates = preferred

    if not candidates:
        raise VideoInfoError("The download finished but no output file was produced.")

    return max(candidates, key=lambda path: (path.stat().st_mtime, path.stat().st_size))
