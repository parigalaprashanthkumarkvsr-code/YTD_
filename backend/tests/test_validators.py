import pytest
from app.core.validators import (
    parse_youtube_url,
    validate_format_id,
    validate_youtube_resource,
    validate_youtube_url,
)


@pytest.mark.parametrize(
    ("raw", "expected_id"),
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ&list=PL123", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?t=30", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("  https://youtu.be/dQw4w9WgXcQ/  ", "dQw4w9WgXcQ"),
    ],
)
def test_valid_urls_are_canonicalised(raw: str, expected_id: str) -> None:
    assert validate_youtube_url(raw) == f"https://www.youtube.com/watch?v={expected_id}"


@pytest.mark.parametrize(
    ("raw", "expected_id"),
    [
        (
            "https://www.youtube.com/playlist?list=PL1234567890",
            "PL1234567890",
        ),
        (
            "https://youtube.com/playlist?list=PL1234567890&si=share",
            "PL1234567890",
        ),
        (
            "https://m.youtube.com/playlist?list=PL1234567890",
            "PL1234567890",
        ),
        (
            "youtube.com/playlist?list=PL1234567890",
            "PL1234567890",
        ),
    ],
)
def test_playlist_urls_are_canonicalised(raw: str, expected_id: str) -> None:
    assert validate_youtube_resource(raw) == f"https://www.youtube.com/playlist?list={expected_id}"
    target = parse_youtube_url(raw)
    assert target.kind == "playlist"
    assert target.id == expected_id


def test_video_validator_still_rejects_playlists() -> None:
    with pytest.raises(ValueError):
        validate_youtube_url("https://www.youtube.com/playlist?list=PL1234567890")


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not a url",
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com:8443/watch?v=dQw4w9WgXcQ",
        "https://user:pass@youtube.com/watch?v=dQw4w9WgXcQ",
        "ftp://youtube.com/watch?v=dQw4w9WgXcQ",
        "javascript:alert(1)",
        "https://www.youtube.com/playlist?list=PL123",
        "https://www.youtube.com/playlist",
        "https://www.youtube.com/playlist?list=../etc/passwd",
        "https://www.youtube.com/@channel",
        "https://www.youtube.com/watch?v=short",
        "https://www.youtube.com/watch?list=PL1234567890",
        "https://youtu.be/",
        "https://youtu.be/dQw4w9WgXcQ/extra",
    ],
)
def test_invalid_urls_are_rejected(raw: str) -> None:
    with pytest.raises(ValueError):
        validate_youtube_url(raw)


def test_format_id_validation() -> None:
    assert validate_format_id("137+140") == "137+140"
    assert validate_format_id("bestaudio") == "bestaudio"
    for bad in ["", "../etc/passwd", "137;rm", "best video", "a" * 65]:
        with pytest.raises(ValueError):
            validate_format_id(bad)
