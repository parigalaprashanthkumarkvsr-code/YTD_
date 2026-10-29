import asyncio
import threading
import time
from pathlib import Path

import pytest
from app.api import info as info_api
from app.core.errors import DownloadCancelledError, VideoUnavailableError
from app.schemas import (
    FormatOption,
    PlaylistInfoResponse,
    PlaylistItem,
    VideoInfoResponse,
)
from app.services import job_manager as job_manager_module
from app.services.job_manager import manager


def sample_info() -> VideoInfoResponse:
    return VideoInfoResponse(
        id="dQw4w9WgXcQ",
        title="Sample video",
        channel="Sample channel",
        duration=212,
        thumbnail="https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        formats=[
            FormatOption(
                format_id="137+140",
                label="1080p MP4",
                ext="mp4",
                height=1080,
                filesize=52_428_800,
            ),
            FormatOption(
                format_id="bestaudio",
                label="Audio only",
                ext="m4a",
                height=None,
                filesize=3_400_000,
            ),
        ],
    )


def sample_playlist() -> PlaylistInfoResponse:
    return PlaylistInfoResponse(
        id="PL1234567890",
        title="Sample playlist",
        channel="Sample channel",
        video_count=2,
        duration=424,
        thumbnail="https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        items=[
            PlaylistItem(
                id="dQw4w9WgXcQ",
                title="First video",
                duration=212,
                thumbnail="https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            ),
            PlaylistItem(
                id="abc123def45",
                title="Second video",
                duration=212,
                thumbnail=None,
            ),
        ],
    )


async def test_health(client) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["ffmpeg"] is True
    assert payload["yt_dlp_version"]


async def test_info_returns_video_and_canonicalises_url(client, monkeypatch) -> None:
    captured: list[str] = []

    async def fake_info(url: str) -> VideoInfoResponse:
        captured.append(url)
        return sample_info()

    monkeypatch.setattr(info_api, "get_media_info", fake_info)

    response = await client.post("/api/info", json={"url": "https://youtu.be/dQw4w9WgXcQ?t=20"})

    assert response.status_code == 200
    assert response.json()["kind"] == "video"
    assert response.json()["title"] == "Sample video"
    assert captured == ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]


async def test_info_returns_playlist_and_canonicalises_url(client, monkeypatch) -> None:
    captured: list[str] = []

    async def fake_info(url: str) -> PlaylistInfoResponse:
        captured.append(url)
        return sample_playlist()

    monkeypatch.setattr(info_api, "get_media_info", fake_info)

    response = await client.post(
        "/api/info",
        json={"url": "https://m.youtube.com/playlist?list=PL1234567890&si=share"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "playlist"
    assert payload["video_count"] == 2
    assert payload["items"][0] == {
        "id": "dQw4w9WgXcQ",
        "title": "First video",
        "duration": 212,
        "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
    }
    assert payload["items"][1]["id"] == "abc123def45"
    assert captured == ["https://www.youtube.com/playlist?list=PL1234567890"]


async def test_info_rejects_non_youtube_url(client) -> None:
    response = await client.post("/api/info", json={"url": "https://example.com/watch?v=abc"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_URL"


async def test_info_rejects_playlist_without_valid_id(client) -> None:
    response = await client.post("/api/info", json={"url": "https://youtube.com/playlist?list=bad"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_URL"


async def test_info_maps_unavailable_video(client, monkeypatch) -> None:
    async def fake_info(url: str) -> VideoInfoResponse:
        raise VideoUnavailableError()

    monkeypatch.setattr(info_api, "get_media_info", fake_info)
    response = await client.post(
        "/api/info", json={"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VIDEO_UNAVAILABLE"


def _fake_run(payload: bytes = b"fake audio bytes", filename: str = "Sample video [abc].mp3"):
    def fake_run(
        *,
        url: str,
        kind: str,
        format_id: str | None,
        audio_format: str,
        job_dir: Path,
        progress,
        cancel_event: threading.Event,
    ) -> Path:
        progress(42.5, "3.2MiB/s", 18, "downloading")
        if cancel_event.is_set():
            raise DownloadCancelledError
        output = job_dir / filename
        output.write_bytes(payload)
        progress(100.0, None, None, "processing")
        return output

    return fake_run


async def _wait_for_status(client, job_id: str, expected: str, attempts: int = 200) -> dict:
    payload: dict = {}
    for _ in range(attempts):
        response = await client.get(f"/api/downloads/{job_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] == expected:
            return payload
        await asyncio.sleep(0.02)
    pytest.fail(f"Job did not reach {expected}; last payload: {payload}")
    return payload


async def test_download_lifecycle_and_file_serving(client, monkeypatch) -> None:
    monkeypatch.setattr(job_manager_module, "run_download", _fake_run())

    response = await client.post(
        "/api/downloads",
        json={
            "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "kind": "audio",
            "audio_format": "mp3",
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    payload = await _wait_for_status(client, job_id, "done")
    assert payload["percent"] == 100.0
    assert payload["filename"] == "Sample video [abc].mp3"

    file_response = await client.get(f"/api/downloads/{job_id}/file")
    assert file_response.status_code == 200
    assert file_response.content == b"fake audio bytes"
    assert "Sample%20video" in file_response.headers["content-disposition"]

    delete_response = await client.delete(f"/api/downloads/{job_id}")
    assert delete_response.status_code == 204
    assert (await client.get(f"/api/downloads/{job_id}")).status_code == 404


async def test_playlist_download_lifecycle(client, monkeypatch) -> None:
    def fake_playlist(
        *,
        url: str,
        kind: str,
        audio_format: str,
        max_height: int | None,
        video_ids: list[str] | None,
        job_dir: Path,
        progress,
        cancel_event: threading.Event,
    ) -> Path:
        assert url == "https://www.youtube.com/playlist?list=PL1234567890"
        assert max_height == 1080
        assert video_ids == ["dQw4w9WgXcQ", "abc123def45"]
        progress(10.0, "2.0MiB/s", 30, "downloading", 1, 2, "First video", 0)
        progress(55.0, None, None, "processing", 2, 2, "Second video", 0)
        output = job_dir / "Sample playlist [PL1234567890].zip"
        output.write_bytes(b"fake zip bytes")
        return output

    monkeypatch.setattr(job_manager_module, "run_playlist_download", fake_playlist)

    response = await client.post(
        "/api/downloads",
        json={
            "url": "https://youtube.com/playlist?list=PL1234567890",
            "kind": "video",
            "max_height": 1080,
            "video_ids": ["dQw4w9WgXcQ", "abc123def45"],
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    payload = await _wait_for_status(client, job_id, "done")
    assert payload["percent"] == 100.0
    assert payload["filename"] == "Sample playlist [PL1234567890].zip"
    assert payload["playlist"]["total_items"] == 2
    assert payload["playlist"]["completed_items"] == 2

    file_response = await client.get(f"/api/downloads/{job_id}/file")
    assert file_response.status_code == 200
    assert file_response.content == b"fake zip bytes"

    delete_response = await client.delete(f"/api/downloads/{job_id}")
    assert delete_response.status_code == 204


async def test_download_rejects_invalid_playlist_quality(client) -> None:
    response = await client.post(
        "/api/downloads",
        json={
            "url": "https://youtube.com/playlist?list=PL1234567890",
            "kind": "video",
            "max_height": 999,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INTERNAL"


async def test_download_rejects_empty_or_invalid_playlist_selection(client) -> None:
    for video_ids in ([], ["not a video id!"]):
        response = await client.post(
            "/api/downloads",
            json={
                "url": "https://youtube.com/playlist?list=PL1234567890",
                "kind": "video",
                "video_ids": video_ids,
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INTERNAL"


async def test_download_reports_failure_and_cleans_files(client, monkeypatch) -> None:
    def failing_run(**kwargs) -> Path:
        raise VideoUnavailableError()

    monkeypatch.setattr(job_manager_module, "run_download", failing_run)

    response = await client.post(
        "/api/downloads",
        json={"url": "https://youtube.com/watch?v=dQw4w9WgXcQ", "kind": "video"},
    )
    job_id = response.json()["job_id"]

    payload = await _wait_for_status(client, job_id, "error")
    assert payload["error"]
    job = manager.require(job_id)
    assert not job.directory.exists()
    assert (await client.get(f"/api/downloads/{job_id}/file")).status_code == 409


async def test_cancel_stops_job_and_removes_files(client, monkeypatch) -> None:
    started = threading.Event()

    def slow_run(
        *,
        url: str,
        kind: str,
        format_id: str | None,
        audio_format: str,
        job_dir: Path,
        progress,
        cancel_event: threading.Event,
    ) -> Path:
        started.set()
        progress(10.0, "1.0MiB/s", 60, "downloading")
        while not cancel_event.is_set():
            time.sleep(0.01)
        raise DownloadCancelledError

    monkeypatch.setattr(job_manager_module, "run_download", slow_run)

    response = await client.post(
        "/api/downloads",
        json={"url": "https://youtube.com/watch?v=dQw4w9WgXcQ", "kind": "video"},
    )
    job_id = response.json()["job_id"]
    assert await asyncio.to_thread(started.wait, 2)

    delete_response = await client.delete(f"/api/downloads/{job_id}")
    assert delete_response.status_code == 204

    payload = await _wait_for_status(client, job_id, "cancelled")
    assert payload["error"] == "Download cancelled."

    job = manager.require(job_id)
    for _ in range(100):
        if not job.directory.exists():
            break
        await asyncio.sleep(0.02)
    assert not job.directory.exists()


async def test_sse_stream_ends_after_done(client, monkeypatch) -> None:
    monkeypatch.setattr(job_manager_module, "run_download", _fake_run(payload=b"stream"))

    response = await client.post(
        "/api/downloads",
        json={"url": "https://youtube.com/watch?v=dQw4w9WgXcQ", "kind": "audio"},
    )
    job_id = response.json()["job_id"]

    async def collect() -> list[str]:
        return [chunk async for chunk in manager.event_stream(job_id)]

    chunks = await asyncio.wait_for(collect(), timeout=5)
    joined = "".join(chunks)
    assert '"status":"queued"' in joined or '"status":"downloading"' in joined
    assert '"status":"done"' in joined


async def test_expired_jobs_are_cleaned_up(client, monkeypatch) -> None:
    monkeypatch.setattr(job_manager_module, "run_download", _fake_run(payload=b"expire"))

    response = await client.post(
        "/api/downloads",
        json={"url": "https://youtube.com/watch?v=dQw4w9WgXcQ", "kind": "audio"},
    )
    job_id = response.json()["job_id"]
    await _wait_for_status(client, job_id, "done")
    directory = manager.require(job_id).directory

    removed = await manager.cleanup_expired(ttl_minutes=0)
    assert removed >= 1
    assert not directory.exists()
    assert (await client.get(f"/api/downloads/{job_id}")).status_code == 404


async def test_missing_job_returns_404(client) -> None:
    response = await client.get("/api/downloads/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INTERNAL"


async def test_invalid_format_id_is_rejected(client) -> None:
    response = await client.post(
        "/api/downloads",
        json={
            "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "kind": "video",
            "format_id": "../etc/passwd",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INTERNAL"
