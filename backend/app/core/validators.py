import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qs, urlsplit

ALLOWED_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"})
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,64}$")
FORMAT_ID_RE = re.compile(r"^[A-Za-z0-9_+.-]{1,64}$")
_PATH_ID_PREFIXES = ("/shorts/", "/live/", "/embed/", "/v/")
_INVALID_URL_MESSAGE = "Please enter a valid YouTube URL."


@dataclass(frozen=True)
class YouTubeTarget:
    """A validated YouTube video or playlist reference."""

    kind: Literal["video", "playlist"]
    id: str
    url: str


def _valid_id(candidate: str | None) -> str | None:
    if candidate and VIDEO_ID_RE.fullmatch(candidate):
        return candidate
    return None


def _valid_playlist_id(candidate: str | None) -> str | None:
    if candidate and PLAYLIST_ID_RE.fullmatch(candidate):
        return candidate
    return None


def parse_youtube_url(raw: str) -> YouTubeTarget:
    """Validate a YouTube video or playlist URL and canonicalise it.

    Only the documented host allow-list is accepted. Playlist URLs are limited
    to ``youtube.com/playlist?list=<id>``; video URLs keep the existing
    canonical ``https://www.youtube.com/watch?v=<id>`` form. Canonical output
    keeps downstream yt-dlp calls deterministic and blocks SSRF attempts.
    """
    if not isinstance(raw, str):
        raise ValueError(_INVALID_URL_MESSAGE)

    value = raw.strip()
    if not value:
        raise ValueError(_INVALID_URL_MESSAGE)

    if "://" not in value:
        value = f"https://{value}"

    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as exc:
        raise ValueError(_INVALID_URL_MESSAGE) from exc

    if parts.scheme.lower() not in {"http", "https"}:
        raise ValueError(_INVALID_URL_MESSAGE)
    if not parts.hostname:
        raise ValueError(_INVALID_URL_MESSAGE)
    # Credentials and explicit ports are never needed for a public YouTube link.
    if parts.username or parts.password or port is not None:
        raise ValueError(_INVALID_URL_MESSAGE)

    host = parts.hostname.lower().rstrip(".")
    if host not in ALLOWED_HOSTS:
        raise ValueError(_INVALID_URL_MESSAGE)

    path = parts.path.rstrip("/")
    query = parse_qs(parts.query)

    if path == "/playlist":
        playlist_id = _valid_playlist_id(query.get("list", [None])[0])
        if playlist_id is None:
            raise ValueError(_INVALID_URL_MESSAGE)
        return YouTubeTarget(
            kind="playlist",
            id=playlist_id,
            url=f"https://www.youtube.com/playlist?list={playlist_id}",
        )

    video_id: str | None = None
    if host == "youtu.be":
        if path.count("/") != 1:
            raise ValueError(_INVALID_URL_MESSAGE)
        video_id = _valid_id(path.lstrip("/"))
    elif path == "/watch":
        video_id = _valid_id(query.get("v", [None])[0])
    else:
        for prefix in _PATH_ID_PREFIXES:
            if path.startswith(prefix):
                video_id = _valid_id(path[len(prefix) :])
                break

    if video_id is None:
        raise ValueError(_INVALID_URL_MESSAGE)

    return YouTubeTarget(
        kind="video",
        id=video_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
    )


def validate_youtube_url(raw: str) -> str:
    """Validate and canonicalise a single-video YouTube URL.

    Playlist URLs are deliberately rejected here so callers that only support
    single videos cannot accidentally treat a playlist as one video.
    """
    target = parse_youtube_url(raw)
    if target.kind != "video":
        raise ValueError(_INVALID_URL_MESSAGE)
    return target.url


def validate_youtube_resource(raw: str) -> str:
    """Validate a YouTube video or playlist URL and return its canonical form."""
    return parse_youtube_url(raw).url


def validate_format_id(raw: str) -> str:
    if not FORMAT_ID_RE.fullmatch(raw):
        raise ValueError("Invalid format selected.")
    return raw
