import threading
import zipfile
from pathlib import Path

import pytest
from app.core.errors import (
    AgeRestrictedError,
    DownloadCancelledError,
    TooLongError,
    VideoUnavailableError,
)
from app.services import ytdlp_service
from app.services.ytdlp_service import (
    _classify_error,
    _extract_playlist_info_sync,
    _playlist_format_selector,
    _PlaylistPayload,
    run_playlist_download,
)
from yt_dlp.utils import DownloadError


def playlist_payload() -> _PlaylistPayload:
    return _PlaylistPayload(
        id="PL1234567890",
        title="Sample: playlist",
        channel="Sample channel",
        duration=300,
        thumbnail="https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        entries=[
            {
                "id": "dQw4w9WgXcQ",
                "title": "First video",
                "duration": 100,
            },
            {
                "id": "abc123def45",
                "title": "Second video",
                "duration": 200,
            },
        ],
    )


def test_playlist_format_selector_caps_quality() -> None:
    best = _playlist_format_selector(None)
    assert best == "bestvideo+bestaudio/best"
    assert "height<=1080" in _playlist_format_selector(1080)
    assert "height<=480" in _playlist_format_selector(480)


def test_network_page_error_is_not_misread_as_age_restriction() -> None:
    error = _classify_error(
        DownloadError(
            "Unable to download API page: connection reset. "
            "Confirm you are on the latest version using yt-dlp -U"
        )
    )
    assert not isinstance(error, AgeRestrictedError)


def test_extract_playlist_info_uses_flat_playlist(monkeypatch) -> None:
    captured_options: dict = {}

    class FakeYDL:
        def __init__(self, options: dict) -> None:
            captured_options.update(options)

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def extract_info(self, url: str, download: bool = False) -> dict:
            assert download is False
            return {
                "id": "PL1234567890",
                "title": "Sample playlist",
                "uploader": "Sample channel",
                "entries": [
                    {
                        "id": "dQw4w9WgXcQ",
                        "title": "First video",
                        "duration": 100,
                        "thumbnails": [{"url": "https://img.example/one.jpg"}],
                    },
                    None,
                    {
                        "id": "abc123def45",
                        "title": "Second video",
                        "duration": 200,
                    },
                ],
            }

    monkeypatch.setattr(ytdlp_service.yt_dlp, "YoutubeDL", FakeYDL)

    info = _extract_playlist_info_sync("https://www.youtube.com/playlist?list=PL1234567890")

    assert info.kind == "playlist"
    assert info.title == "Sample playlist"
    assert info.channel == "Sample channel"
    assert info.video_count == 2
    assert info.duration == 300
    assert info.thumbnail == "https://img.example/one.jpg"
    assert [item.id for item in info.items] == ["dQw4w9WgXcQ", "abc123def45"]
    assert info.items[0].title == "First video"
    assert info.items[0].duration == 100
    assert info.items[0].thumbnail == "https://img.example/one.jpg"
    assert info.items[1].thumbnail is None
    assert captured_options["extract_flat"] == "in_playlist"
    assert captured_options["noplaylist"] is False


def test_extract_playlist_info_rejects_oversized_playlist(monkeypatch) -> None:
    class FakeYDL:
        def __init__(self, options: dict) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def extract_info(self, url: str, download: bool = False) -> dict:
            return {
                "id": "PL1234567890",
                "title": "Huge playlist",
                "entries": [
                    {"id": f"video{i:05d}", "title": f"Video {i}"}
                    for i in range(ytdlp_service.settings.max_playlist_items + 1)
                ],
            }

    monkeypatch.setattr(ytdlp_service.yt_dlp, "YoutubeDL", FakeYDL)

    with pytest.raises(TooLongError):
        _extract_playlist_info_sync("https://www.youtube.com/playlist?list=PL1234567890")


def test_run_playlist_download_builds_zip(monkeypatch, tmp_path: Path) -> None:
    def fake_run_download(
        *,
        url: str,
        kind: str,
        format_id: str | None,
        audio_format: str,
        job_dir: Path,
        progress,
        cancel_event: threading.Event,
    ) -> Path:
        assert format_id and "height<=1080" in format_id
        job_dir.mkdir(parents=True, exist_ok=True)
        video_id = url.rsplit("=", 1)[-1]
        output = job_dir / f"{video_id} [id].mp4"
        output.write_bytes(b"video")
        progress(50.0, None, None, "downloading")
        progress(100.0, None, None, "processing")
        return output

    monkeypatch.setattr(
        ytdlp_service, "_extract_playlist_payload_sync", lambda url: playlist_payload()
    )
    monkeypatch.setattr(ytdlp_service, "run_download", fake_run_download)

    events: list[tuple] = []

    def record(*args) -> None:
        events.append(args)

    output = run_playlist_download(
        url="https://www.youtube.com/playlist?list=PL1234567890",
        kind="video",
        audio_format="mp3",
        max_height=1080,
        job_dir=tmp_path,
        progress=record,
        cancel_event=threading.Event(),
    )

    assert output.suffix == ".zip"
    assert output.name == "Sample_ playlist.zip"
    with zipfile.ZipFile(output) as archive:
        names = sorted(archive.namelist())
        assert names == ["abc123def45 [id].mp4", "dQw4w9WgXcQ [id].mp4"]
    assert events[-1][3] == "processing"
    assert events[-1][4] == 2
    assert events[-1][5] == 2


def test_run_playlist_download_only_downloads_selected_items(monkeypatch, tmp_path: Path) -> None:
    downloaded: list[str] = []

    def fake_run_download(**kwargs) -> Path:
        video_id = kwargs["url"].rsplit("=", 1)[-1]
        downloaded.append(video_id)
        job_dir = kwargs["job_dir"]
        job_dir.mkdir(parents=True, exist_ok=True)
        output = job_dir / f"{video_id}.mp4"
        output.write_bytes(b"video")
        return output

    monkeypatch.setattr(
        ytdlp_service, "_extract_playlist_payload_sync", lambda url: playlist_payload()
    )
    monkeypatch.setattr(ytdlp_service, "run_download", fake_run_download)

    events: list[tuple] = []
    output = run_playlist_download(
        url="https://www.youtube.com/playlist?list=PL1234567890",
        kind="video",
        audio_format="mp3",
        max_height=None,
        job_dir=tmp_path,
        progress=lambda *args: events.append(args),
        cancel_event=threading.Event(),
        video_ids=["abc123def45"],
    )

    assert downloaded == ["abc123def45"]
    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == ["abc123def45.mp4"]
    assert events[-1][4] == 1
    assert events[-1][5] == 1


def test_run_playlist_download_counts_missing_selection_as_skipped(
    monkeypatch, tmp_path: Path
) -> None:
    def fake_run_download(**kwargs) -> Path:
        job_dir = kwargs["job_dir"]
        job_dir.mkdir(parents=True, exist_ok=True)
        output = job_dir / "First video.mp4"
        output.write_bytes(b"video")
        return output

    monkeypatch.setattr(
        ytdlp_service, "_extract_playlist_payload_sync", lambda url: playlist_payload()
    )
    monkeypatch.setattr(ytdlp_service, "run_download", fake_run_download)

    events: list[tuple] = []
    output = run_playlist_download(
        url="https://www.youtube.com/playlist?list=PL1234567890",
        kind="video",
        audio_format="mp3",
        max_height=None,
        job_dir=tmp_path,
        progress=lambda *args: events.append(args),
        cancel_event=threading.Event(),
        video_ids=["dQw4w9WgXcQ", "zzzzzzzzzzz"],
    )

    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == ["First video.mp4"]
    assert events[-1][4] == 2
    assert events[-1][5] == 2
    assert events[-1][7] == 1


def test_run_playlist_download_skips_unavailable_items(monkeypatch, tmp_path: Path) -> None:
    calls = 0

    def fake_run_download(**kwargs) -> Path:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise VideoUnavailableError()
        job_dir = kwargs["job_dir"]
        job_dir.mkdir(parents=True, exist_ok=True)
        output = job_dir / "Second video [abc].mp4"
        output.write_bytes(b"video")
        return output

    monkeypatch.setattr(
        ytdlp_service, "_extract_playlist_payload_sync", lambda url: playlist_payload()
    )
    monkeypatch.setattr(ytdlp_service, "run_download", fake_run_download)

    events: list[tuple] = []
    output = run_playlist_download(
        url="https://www.youtube.com/playlist?list=PL1234567890",
        kind="video",
        audio_format="mp3",
        max_height=None,
        job_dir=tmp_path,
        progress=lambda *args: events.append(args),
        cancel_event=threading.Event(),
    )

    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == ["Second video [abc].mp4"]
    assert events[-1][7] == 1


def test_run_playlist_download_fails_when_all_items_fail(monkeypatch, tmp_path: Path) -> None:
    def failing_run(**kwargs) -> Path:
        raise VideoUnavailableError()

    monkeypatch.setattr(
        ytdlp_service, "_extract_playlist_payload_sync", lambda url: playlist_payload()
    )
    monkeypatch.setattr(ytdlp_service, "run_download", failing_run)

    with pytest.raises(VideoUnavailableError, match="No videos"):
        run_playlist_download(
            url="https://www.youtube.com/playlist?list=PL1234567890",
            kind="audio",
            audio_format="mp3",
            max_height=None,
            job_dir=tmp_path,
            progress=lambda *args: None,
            cancel_event=threading.Event(),
        )


def test_run_playlist_download_honours_cancel(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        ytdlp_service, "_extract_playlist_payload_sync", lambda url: playlist_payload()
    )

    def cancelling_run(**kwargs) -> Path:
        kwargs["cancel_event"].set()
        raise DownloadCancelledError

    monkeypatch.setattr(ytdlp_service, "run_download", cancelling_run)

    with pytest.raises(DownloadCancelledError):
        run_playlist_download(
            url="https://www.youtube.com/playlist?list=PL1234567890",
            kind="video",
            audio_format="mp3",
            max_height=None,
            job_dir=tmp_path,
            progress=lambda *args: None,
            cancel_event=threading.Event(),
        )


def test_run_playlist_download_stops_before_extraction_when_cancelled(
    monkeypatch, tmp_path: Path
) -> None:
    cancel_event = threading.Event()
    cancel_event.set()
    monkeypatch.setattr(
        ytdlp_service,
        "_extract_playlist_payload_sync",
        lambda url: pytest.fail("playlist should not be extracted after cancellation"),
    )

    with pytest.raises(DownloadCancelledError):
        run_playlist_download(
            url="https://www.youtube.com/playlist?list=PL1234567890",
            kind="video",
            audio_format="mp3",
            max_height=None,
            job_dir=tmp_path,
            progress=lambda *args: None,
            cancel_event=cancel_event,
        )
