# YTD — YouTube Downloader

A clean, self-hosted YouTube downloader. Paste a video or playlist URL, preview
it, pick a format, and save the file. Video (MP4) and audio-only (MP3 / M4A)
downloads run through `yt-dlp` and `ffmpeg`, with live progress over Server-Sent
Events. Playlists are bundled into a single ZIP.

Built from [`PRD.md`](./PRD.md) and [`DESIGN.md`](./DESIGN.md) with the Tundora +
Sandal palette, JetBrains Mono, and a font-based `YTD_` wordmark.

**Repository:** <https://github.com/parigalaprashanthkumarkvsr-code/YTD_.git>

> **Legal notice:** Downloading from YouTube may violate its Terms of Service
> unless the content is yours, Creative Commons / public domain, or you have
> permission. YTD is intended for personal, lawful use only. It does not bypass
> DRM, age gates, region locks, or sign-in restrictions.

## Features

- URL allow-list for `youtube.com`, `www.youtube.com`, `m.youtube.com`, and `youtu.be`
- Metadata preview: title, channel, duration, thumbnail, formats
- Video quality picker with file-size estimates; MP4 merge via ffmpeg
- Audio extraction to MP3 (192 kbps) or M4A
- Playlist preview lists every video with its title, thumbnail, and duration
- Per-video selection: check only the items you want, with select-all and clear
  controls, then download the checked videos (up to `MAX_PLAYLIST_ITEMS`,
  default 50) as one ZIP with a quality cap applied to every item
- Live progress with current playlist item, speed, ETA, and cancel
- Finished-file serving with safe filenames and automatic TTL cleanup
- In-browser download history (`localStorage`)
- Dark theme by default and an accessible light theme
- Rate limiting, CORS allow-list, Pydantic validation, and random job IDs
- Docker Compose deployment and CI for lint, tests, and builds

## How to use the app

1. Paste a YouTube video or playlist URL and click **Fetch**.
2. Check the preview. Video links show title, channel, duration, and formats;
   playlist links show the video count and a checklist of every video.
3. For a playlist, check the videos you want. Nothing is checked initially; use
   **select all** to include the whole playlist or **clear** to start over.
4. Choose **Video** and a quality, or **Audio** and MP3/M4A.
5. Click **Download** and follow the progress bar. Use **Cancel** to stop.
6. When it finishes, click **Save file** (or **Save ZIP** for a playlist).
7. Finished downloads appear under **History** for quick re-download while the
   server still has the file.

Playlist URLs use the `youtube.com/playlist?list=...` form. A watch link with a
`list=` parameter still downloads only that single video. Playlist downloads
include only the checked videos; the progress count reflects that selection.

## Quick start with Docker

```bash
git clone https://github.com/parigalaprashanthkumarkvsr-code/YTD_.git
cd YTD_
cp .env.example .env
docker compose up --build
```

Open **http://localhost:5173**. The API and OpenAPI docs are available at
**http://localhost:8000/docs**.

The download directory is a named volume, but it is treated as ephemeral: active
leftovers are cleared at startup and completed files expire after
`FILE_TTL_MINUTES` (default 30).

## Run locally (without Docker)

Requirements:

- Python **3.12+**
- Node.js **20+** and npm
- `ffmpeg` installed and available on your `PATH`
- `git`

On Arch Linux the system prerequisites can be installed with:

```bash
sudo pacman -S ffmpeg python nodejs npm git
```

On macOS with Homebrew:

```bash
brew install ffmpeg python node git
```

### 1. Clone the repository

```bash
git clone https://github.com/parigalaprashanthkumarkvsr-code/YTD_.git
cd YTD_
```

### 2. Start the backend

In one terminal:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

The API is now at **http://localhost:8000**, and the interactive API docs are
at **http://localhost:8000/docs**. Check it with:

```bash
curl http://localhost:8000/api/health
```

`backend/.env.example` lists the available backend settings. Copy it to
`backend/.env` if you want to override the defaults:

```bash
cp .env.example .env
```

### 3. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite serves the UI at **http://localhost:5173** and proxies `/api` requests to
the backend on port 8000. Leave both terminals running while you use the app.

### Tests and checks

```bash
# backend
cd backend
pytest -q
ruff check .
black --check .

# frontend
cd frontend
npm run test
npm run lint
npm run typecheck
npm run build
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DOWNLOAD_DIR` | `/tmp/ytd-downloads` | Per-job download folders |
| `FILE_TTL_MINUTES` | `30` | How long finished files are kept |
| `MAX_CONCURRENT_JOBS` | `3` | Concurrent yt-dlp workers |
| `MAX_DURATION_SECONDS` | `7200` | Reject longer videos |
| `MAX_FILESIZE_MB` | `4096` | Per-file size cap |
| `MAX_PLAYLIST_ITEMS` | `50` | Maximum videos accepted from one playlist |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | CORS origins |
| `RATE_LIMIT` | `10/minute` | `slowapi` limit for metadata/job creation |
| `RATE_LIMIT_ENABLED` | `true` | Disable only for tests/local experiments |
| `CLEANUP_INTERVAL_SECONDS` | `60` | TTL cleanup cadence |

The frontend optionally reads `VITE_API_BASE` (default `/api`).

## API

Base path: `/api`

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Status, `yt-dlp` version, ffmpeg availability |
| `POST` | `/info` | `{url}` → video metadata + formats, or playlist metadata |
| `POST` | `/downloads` | `{url, kind, format_id?, audio_format?, max_height?, video_ids?}` → `{job_id}` |
| `GET` | `/downloads/{id}` | Job snapshot |
| `GET` | `/downloads/{id}/events` | SSE progress stream |
| `GET` | `/downloads/{id}/file` | Finished file |
| `DELETE` | `/downloads/{id}` | Cancel active job / clean up finished job |

Errors use one shape:

```json
{ "error": { "code": "INVALID_URL", "message": "Please enter a valid YouTube URL." } }
```

Codes: `INVALID_URL`, `VIDEO_UNAVAILABLE`, `AGE_RESTRICTED`, `REGION_BLOCKED`,
`TOO_LONG`, `RATE_LIMITED`, `INTERNAL`.

For a playlist URL, `POST /info` returns `kind: "playlist"`, `video_count`, and
an `items` array describing every available video:

```json
{
  "kind": "playlist",
  "id": "PL1234567890",
  "title": "Playlist title",
  "video_count": 2,
  "items": [
    {
      "id": "dQw4w9WgXcQ",
      "title": "First video",
      "duration": 212,
      "thumbnail": "https://..."
    },
    {
      "id": "abc123def45",
      "title": "Second video",
      "duration": 180,
      "thumbnail": "https://..."
    }
  ]
}
```

To download a selection, pass `video_ids` (an array of the `id` values from
`items`) to `POST /downloads`. Omit it to download every available item. The
optional `max_height` (`2160`, `1440`, `1080`, `720`, `480`, or `360`; omit for
best available) applies to every selected item, and the finished files are served
as one ZIP. Progress snapshots and SSE events include a `playlist` object whose
`total_items` is the number of selected videos:

```json
{
  "total_items": 7,
  "completed_items": 4,
  "current_item": 5,
  "current_title": "Lecture 05",
  "skipped_items": 1
}
```

## Project layout

```text
backend/
  app/
    api/          # health, info, downloads routers
    core/         # validation, errors, filenames, rate limit
    services/     # yt-dlp wrapper, job manager, TTL cleanup
    main.py       # FastAPI app, CORS, lifespan, error handlers
  tests/
frontend/
  src/
    api/          # typed fetch client
    components/   # logo, URL form, preview, picker, progress, history
    hooks/        # metadata mutation, download + EventSource, history
    styles/       # Tundora + Sandal tokens
    lib/          # URL validation, formatting
  public/favicon.svg
docker-compose.yml
```

## Notes and limitations

- **Playlists:** use a `youtube.com/playlist?list=...` URL. A `watch?v=...&list=...`
  link downloads that single video. Check the videos you want in the playlist
  preview, or use **select all** for the whole playlist. Only checked items are
  bundled into the ZIP. Unavailable, private, or over-limit items are skipped,
  and the job reports how many were skipped. Playlists longer than
  `MAX_PLAYLIST_ITEMS` are rejected.
- **v1 scope:** subtitle downloads, accounts, DRM, and bypassing age/region
  restrictions are intentionally out of scope. Private, age-restricted, and
  region-blocked videos return a readable error.
- **YouTube changes often.** `yt-dlp` is pinned in `backend/requirements.txt`.
  If extraction starts failing, bump the pin and rebuild:
  `pip install -U yt-dlp` locally or `docker compose build --no-cache backend`.
- **Jobs are in-process.** Restarting the backend cancels active jobs; finished
  files are removed at the next startup because the download directory is
  ephemeral by design.
- **History is browser-local.** It stores titles and job links only; files still
  expire server-side.
