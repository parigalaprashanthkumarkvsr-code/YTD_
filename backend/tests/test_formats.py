from app.services.ytdlp_service import _build_formats


def base_info() -> dict:
    return {
        "formats": [
            {
                "format_id": "140",
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "mp4a.40.2",
                "abr": 128,
                "filesize": 3_000_000,
            },
            {
                "format_id": "251",
                "ext": "webm",
                "vcodec": "none",
                "acodec": "opus",
                "abr": 160,
                "filesize": 3_500_000,
            },
            {
                "format_id": "137",
                "ext": "mp4",
                "vcodec": "avc1",
                "acodec": "none",
                "height": 1080,
                "tbr": 4000,
                "filesize": 50_000_000,
            },
            {
                "format_id": "248",
                "ext": "webm",
                "vcodec": "vp9",
                "acodec": "none",
                "height": 1080,
                "tbr": 4500,
                "filesize": 55_000_000,
            },
            {
                "format_id": "136",
                "ext": "mp4",
                "vcodec": "avc1",
                "acodec": "none",
                "height": 720,
                "tbr": 2000,
                "filesize": 25_000_000,
            },
            {
                "format_id": "22",
                "ext": "mp4",
                "vcodec": "avc1",
                "acodec": "mp4a.40.2",
                "height": 720,
                "tbr": 1500,
                "filesize": 20_000_000,
            },
        ]
    }


def test_prefers_mp4_video_plus_m4a_audio() -> None:
    formats = _build_formats(base_info())
    by_height = {fmt.height: fmt for fmt in formats if fmt.height}

    assert by_height[1080].format_id == "137+140"
    assert by_height[1080].label == "1080p MP4"
    assert by_height[1080].filesize == 53_000_000
    assert by_height[720].format_id == "136+140"
    assert formats[-1].format_id == "bestaudio"
    assert formats[-1].ext == "m4a"


def test_falls_back_to_webm_when_no_mp4_video() -> None:
    info = {
        "formats": [
            {
                "format_id": "251",
                "ext": "webm",
                "vcodec": "none",
                "acodec": "opus",
                "abr": 160,
                "filesize": 3_500_000,
            },
            {
                "format_id": "248",
                "ext": "webm",
                "vcodec": "vp9",
                "acodec": "none",
                "height": 1080,
                "tbr": 4500,
                "filesize": 55_000_000,
            },
        ]
    }
    formats = _build_formats(info)
    assert formats[0].format_id == "248+251"
    assert formats[0].label == "1080p WEBM"
    assert formats[0].ext == "webm"


def test_skips_audio_only_formats_for_video_list() -> None:
    formats = _build_formats(base_info())
    assert all(fmt.height is not None for fmt in formats[:-1])


def test_progress_is_weighted_across_merged_streams() -> None:
    import threading

    from app.services.ytdlp_service import _make_progress_hook

    events: list[tuple[float, str]] = []

    def record(percent: float, speed: str | None, eta: int | None, status: str) -> None:
        events.append((percent, status))

    hook = _make_progress_hook(record, threading.Event(), expected_streams=2)
    hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100})
    hook({"status": "finished"})
    hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100})
    hook({"status": "finished"})

    assert [percent for percent, _ in events] == [25.0, 50.0, 75.0, 99.0]
    assert all(status == "downloading" for _, status in events)


def test_estimates_missing_filesizes_from_bitrate() -> None:
    formats = _build_formats(
        {
            "duration": 100,
            "formats": [
                {
                    "format_id": "140",
                    "ext": "m4a",
                    "vcodec": "none",
                    "acodec": "mp4a.40.2",
                    "abr": 128,
                },
                {
                    "format_id": "137",
                    "ext": "mp4",
                    "vcodec": "avc1",
                    "acodec": "none",
                    "height": 1080,
                    "tbr": 1000,
                },
            ],
        }
    )
    video = formats[0]
    assert video.filesize == 14_100_000
    assert formats[-1].filesize == 1_600_000
