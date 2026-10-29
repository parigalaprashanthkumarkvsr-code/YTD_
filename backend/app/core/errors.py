from typing import Final, Literal

ErrorCode = Literal[
    "INVALID_URL",
    "VIDEO_UNAVAILABLE",
    "AGE_RESTRICTED",
    "REGION_BLOCKED",
    "TOO_LONG",
    "RATE_LIMITED",
    "INTERNAL",
]

DEFAULT_STATUS: Final[dict[str, int]] = {
    "INVALID_URL": 400,
    "VIDEO_UNAVAILABLE": 422,
    "AGE_RESTRICTED": 403,
    "REGION_BLOCKED": 451,
    "TOO_LONG": 422,
    "RATE_LIMITED": 429,
    "INTERNAL": 500,
}


class AppError(Exception):
    """Base class for errors that are safe to expose through the API."""

    code: ErrorCode = "INTERNAL"
    status_code: int = 500
    default_message: str = "Something went wrong. Please try again."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: ErrorCode | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.default_message
        if code is not None:
            self.code = code
        if status_code is not None:
            resolved_status = status_code
        elif type(self).status_code != AppError.status_code:
            resolved_status = type(self).status_code
        else:
            resolved_status = DEFAULT_STATUS[self.code]
        self.status_code = resolved_status
        super().__init__(self.message)


class InvalidUrlError(AppError):
    code = "INVALID_URL"
    default_message = "Please enter a valid YouTube URL."


class VideoUnavailableError(AppError):
    code = "VIDEO_UNAVAILABLE"
    default_message = "This video is unavailable. It may be private, removed, or a live stream."


class AgeRestrictedError(AppError):
    code = "AGE_RESTRICTED"
    default_message = "This video is age-restricted and cannot be downloaded."


class RegionBlockedError(AppError):
    code = "REGION_BLOCKED"
    default_message = "This video is not available in your region."


class TooLongError(AppError):
    code = "TOO_LONG"
    default_message = "This video is longer than the allowed limit."


class RateLimitedError(AppError):
    code = "RATE_LIMITED"
    default_message = "Too many requests. Please wait a moment and try again."


class NotFoundError(AppError):
    code = "INTERNAL"
    status_code = 404
    default_message = "Download not found."


class FileNotReadyError(AppError):
    code = "INTERNAL"
    status_code = 409
    default_message = "The file is not ready yet."


class DownloadCancelledError(Exception):
    """Raised inside the yt-dlp worker when a job is cancelled."""


class VideoInfoError(AppError):
    """Raised when metadata extraction fails for a reason we cannot classify."""

    code = "INTERNAL"
    default_message = "Could not fetch video details. Please try again."
