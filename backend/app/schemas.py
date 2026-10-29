from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.core.validators import (
    VIDEO_ID_RE,
    validate_format_id,
    validate_youtube_resource,
)

JobStatus = Literal["queued", "downloading", "processing", "done", "error", "cancelled"]
AudioFormat = Literal["mp3", "m4a"]
PlaylistQuality = Literal[2160, 1440, 1080, 720, 480, 360]


class InfoRequest(BaseModel):
    url: HttpUrl

    @field_validator("url", mode="before")
    @classmethod
    def check_url(cls, value: object) -> str:
        if not isinstance(value, (str, HttpUrl)):
            raise ValueError("Please enter a valid YouTube URL.")
        return validate_youtube_resource(str(value))


class DownloadRequest(BaseModel):
    url: HttpUrl
    kind: Literal["video", "audio"] = "video"
    format_id: str | None = Field(default=None, max_length=64)
    audio_format: AudioFormat = "mp3"
    max_height: PlaylistQuality | None = None
    video_ids: list[str] | None = Field(default=None, max_length=200)

    @field_validator("url", mode="before")
    @classmethod
    def check_url(cls, value: object) -> str:
        if not isinstance(value, (str, HttpUrl)):
            raise ValueError("Please enter a valid YouTube URL.")
        return validate_youtube_resource(str(value))

    @field_validator("format_id")
    @classmethod
    def check_format_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_format_id(value)

    @field_validator("video_ids")
    @classmethod
    def check_video_ids(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        unique: list[str] = []
        for raw in value:
            if not isinstance(raw, str) or not VIDEO_ID_RE.fullmatch(raw):
                raise ValueError("One of the selected videos is invalid.")
            if raw not in unique:
                unique.append(raw)
        if not unique:
            raise ValueError("Select at least one video from the playlist.")
        return unique


class FormatOption(BaseModel):
    format_id: str
    label: str
    ext: str
    height: int | None = None
    filesize: int | None = None


class VideoInfoResponse(BaseModel):
    kind: Literal["video"] = "video"
    id: str
    title: str
    channel: str
    duration: int
    thumbnail: str | None
    formats: list[FormatOption]


class PlaylistItem(BaseModel):
    id: str
    title: str
    duration: int
    thumbnail: str | None


class PlaylistInfoResponse(BaseModel):
    kind: Literal["playlist"] = "playlist"
    id: str
    title: str
    channel: str
    video_count: int
    duration: int
    thumbnail: str | None
    items: list[PlaylistItem]


MediaInfoResponse = Annotated[
    VideoInfoResponse | PlaylistInfoResponse,
    Field(discriminator="kind"),
]


class DownloadAccepted(BaseModel):
    job_id: str


class PlaylistProgress(BaseModel):
    total_items: int
    completed_items: int = 0
    current_item: int | None = None
    current_title: str | None = None
    skipped_items: int = 0


class JobState(BaseModel):
    id: str
    status: JobStatus
    percent: float = 0
    speed: str | None = None
    eta: int | None = None
    filename: str | None = None
    error: str | None = None
    created_at: datetime
    playlist: PlaylistProgress | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    yt_dlp_version: str
    ffmpeg: bool
