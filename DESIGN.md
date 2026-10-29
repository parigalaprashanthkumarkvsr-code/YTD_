# YouTube Downloader (YTD) — Design

**Document:** Technical & UX Design
**Stack:** React (Vite + TypeScript) frontend · Python (FastAPI + yt-dlp + ffmpeg) backend
**Brand:** Font-based `YTD_` logo · monospace type · Tundora + Sandal palette
**Status:** Draft v1.2 (playlist extension)
**Related:** `PRD.md` (requirements) · `AGENT.md` (coding-agent instructions)

> **Assumptions:** single-user / self-hosted tool, no login in v1, runs locally or in Docker.

---

## 1. Architecture

```
┌──────────────┐   HTTP/JSON + SSE   ┌─────────────────────────────┐
│ React (Vite) │ ──────────────────▶ │ FastAPI                     │
│ TS + Tailwind│ ◀────────────────── │  ├─ routers (api/)          │
└──────────────┘                     │  ├─ services (yt-dlp wrapper)│
                                     │  ├─ job manager (asyncio)   │
                                     │  └─ cleanup scheduler       │
                                     └──────────┬──────────────────┘
                                                │
                                     ┌──────────▼─────────┐
                                     │ yt-dlp + ffmpeg    │
                                     │ /tmp/downloads/<id>│
                                     └────────────────────┘
```

## 2. Tech Choices
| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18 + Vite + TypeScript | Fast dev, type safety |
| Styling | Tailwind CSS | Quick, consistent UI |
| Data fetching | TanStack Query | Caching, retries, loading states |
| Backend | FastAPI | Async, auto OpenAPI docs, Pydantic validation |
| Downloader | `yt-dlp` (Python API, not shell) | Actively maintained, handles format merging |
| Media | `ffmpeg` | Merge streams, extract audio |
| Jobs | In-process `asyncio` + thread pool | Simple for v1; swap to Celery/RQ later |
| Progress | Server-Sent Events | One-way stream, simpler than WebSockets |
| Fonts | `@fontsource/jetbrains-mono` (self-hosted) | Monospace UI + logo, no external font requests |
| Packaging | Docker Compose | One-command run |

## 3. API Design

Base path: `/api`

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Status + `yt-dlp` version |
| POST | `/info` | Body `{url}` → video metadata + formats, or playlist metadata |
| POST | `/downloads` | Body `{url, format_id?, kind, audio_format?, max_height?}` → `{job_id}` |
| GET | `/downloads/{id}` | Job status snapshot |
| GET | `/downloads/{id}/events` | SSE progress stream |
| GET | `/downloads/{id}/file` | Download the finished file |
| DELETE | `/downloads/{id}` | Cancel + clean up |

**`POST /info` response (video)**
```json
{
  "kind": "video",
  "id": "dQw4w9WgXcQ",
  "title": "Video title",
  "channel": "Channel name",
  "duration": 212,
  "thumbnail": "https://...",
  "formats": [
    {"format_id": "137+140", "label": "1080p MP4", "ext": "mp4", "height": 1080, "filesize": 52428800},
    {"format_id": "bestaudio", "label": "Audio only", "ext": "m4a", "filesize": 3400000}
  ]
}
```

**`POST /info` response (playlist)**
```json
{
  "kind": "playlist",
  "id": "PL1234567890",
  "title": "Playlist title",
  "channel": "Channel name",
  "video_count": 12,
  "duration": 5400,
  "thumbnail": "https://..."
}
```

Playlist downloads use `max_height` (`2160 | 1440 | 1080 | 720 | 480 | 360`;
omit for best available) and serve one ZIP containing every available item.
Playlist length is capped by `MAX_PLAYLIST_ITEMS` (default 50).

**SSE event payload**
```json
{"status": "downloading", "percent": 42.5, "speed": "3.2MiB/s", "eta": 18}
```
`status` ∈ `queued | downloading | processing | done | error | cancelled`

Playlist events add:
```json
{"playlist": {"total_items": 12, "completed_items": 4, "current_item": 5, "current_title": "Lecture 05", "skipped_items": 1}}
```

**Error format** (all endpoints)
```json
{"error": {"code": "INVALID_URL", "message": "Please enter a valid YouTube URL."}}
```
Codes: `INVALID_URL`, `VIDEO_UNAVAILABLE`, `AGE_RESTRICTED`, `REGION_BLOCKED`, `TOO_LONG`, `RATE_LIMITED`, `INTERNAL`.

## 4. Data Models (Pydantic)
```python
class InfoRequest(BaseModel):
    url: HttpUrl

class PlaylistInfoResponse(BaseModel):
    kind: Literal["playlist"] = "playlist"
    id: str
    title: str
    channel: str
    video_count: int
    duration: int
    thumbnail: str | None

class DownloadRequest(BaseModel):
    url: HttpUrl
    kind: Literal["video", "audio"] = "video"
    format_id: str | None = None
    audio_format: Literal["mp3", "m4a"] = "mp3"
    max_height: Literal[2160, 1440, 1080, 720, 480, 360] | None = None

class PlaylistProgress(BaseModel):
    total_items: int
    completed_items: int = 0
    current_item: int | None = None
    current_title: str | None = None
    skipped_items: int = 0

class JobState(BaseModel):
    id: str
    status: Literal["queued","downloading","processing","done","error","cancelled"]
    percent: float = 0
    speed: str | None = None
    eta: int | None = None
    filename: str | None = None
    error: str | None = None
    created_at: datetime
    playlist: PlaylistProgress | None = None
```

## 5. Backend Structure
```
backend/
├─ app/
│  ├─ main.py            # FastAPI app, CORS, routers, lifespan (cleanup task)
│  ├─ config.py          # Settings via pydantic-settings (env vars)
│  ├─ api/
│  │  ├─ info.py
│  │  └─ downloads.py
│  ├─ services/
│  │  ├─ ytdlp_service.py   # extract_info(), run_download(), run_playlist_download()
│  │  ├─ job_manager.py     # job registry, queues, cancel
│  │  └─ cleanup.py         # TTL deletion loop
│  ├─ core/
│  │  ├─ validators.py      # URL allow-list
│  │  ├─ errors.py          # custom exceptions → JSON handlers
│  │  └─ rate_limit.py
│  └─ schemas.py
├─ tests/
├─ requirements.txt
└─ Dockerfile
```

### Key backend rules
- Call `yt_dlp.YoutubeDL` via its Python API with a `progress_hooks` callback. **Never** build shell strings.
- Run blocking yt-dlp calls in a thread (`asyncio.to_thread`); push progress into an `asyncio.Queue` per job for SSE.
- Each job gets its own folder: `DOWNLOAD_DIR/<job_id>/`.
- Sanitize filenames; send `Content-Disposition` with a safe name.
- Config via env: `DOWNLOAD_DIR`, `FILE_TTL_MINUTES=30`, `MAX_CONCURRENT_JOBS=3`, `MAX_DURATION_SECONDS=7200`, `ALLOWED_ORIGINS`.

## 6. Frontend Structure
```
frontend/
├─ src/
│  ├─ main.tsx
│  ├─ App.tsx
│  ├─ api/client.ts          # fetch wrappers + types
│  ├─ hooks/
│  │  ├─ useVideoInfo.ts     # TanStack mutation → /info
│  │  └─ useDownload.ts      # start job + EventSource progress
│  ├─ components/
│  │  ├─ Logo.tsx            # font-based YTD_ wordmark (text, not an image)
│  │  ├─ UrlForm.tsx
│  │  ├─ VideoCard.tsx       # thumbnail, title, duration
│  │  ├─ FormatPicker.tsx    # video/audio tabs + quality list
│  │  ├─ PlaylistOptions.tsx # playlist quality cap + audio tabs
│  │  ├─ ProgressBar.tsx
│  │  ├─ ErrorBanner.tsx
│  │  ├─ HistoryList.tsx
│  │  └─ LegalNotice.tsx
│  ├─ styles/tokens.css      # CSS variables for the palette (see Brand section)
│  ├─ types.ts
│  └─ index.css
├─ public/favicon.svg        # text-based Y_ mark in Sandal on Tundora
├─ tailwind.config.ts        # maps tokens + mono font family
├─ vite.config.ts            # dev proxy /api → :8000
└─ package.json
```

## 7. UI / UX Design

**Main flow (single page)**
1. **Hero input:** large URL field + "Fetch" button; paste auto-detects.
2. **Preview card:** thumbnail, title, channel, duration, or playlist item count.
3. **Options:** tabs `Video | Audio`, quality radio list with file size estimates. Playlists show a quality cap and a ZIP notice.
4. **Download button** → becomes a **progress bar** (percent, current item, speed, ETA, Cancel).
5. **Done state:** "Save file" (or "Save ZIP") button + "Download another".

**States to design:** empty, loading (skeleton card), error (inline banner with retry), in-progress, success.

**Visual style:** terminal-inspired but clean. Centered, max-width ~720px, small-radius cards (6–8px), Sandal as the single accent, dark theme by default (light theme optional), large tap targets for mobile. Everything is set in monospace. See the Brand section below.

**Accessibility:** labelled inputs, `aria-live` region for progress and errors, visible focus rings, keyboard-operable.

## 7.1 Brand & Visual Identity

### Color palette (from `Tundora_to_Sandal.svg`)

| Token | Name | Hex | RGB | Pantone |
|---|---|---|---|---|
| `--tundora-300` | Tundora Light 02 | `#75696C` | 117, 105, 108 | 437 C |
| `--tundora-400` | Tundora Light 01 | `#5B4F52` | 91, 79, 82 | 411 C |
| `--tundora-500` | Tundora | `#473D3F` | 71, 61, 63 | 446 C |
| `--tundora-600` | Tundora Dark 01 | `#3A3133` | 58, 49, 51 | — |
| `--sandal-200` | Sandal Light 01 | `#D9B693` | 217, 182, 147 | — |
| `--sandal-300` | Sandal | `#B99271` | 185, 146, 113 | — |
| `--sandal-400` | Sandal Dark 01 | `#A17858` | 161, 120, 88 | — |
| `--sandal-500` | Sandal Dark 02 | `#875F43` | 135, 95, 67 | — |

**Additions that are not in your palette** (the palette has no light neutral or status colors, so these are the only extras):

| Token | Hex | Use |
|---|---|---|
| `--paper` | `#F3E9DD` | Primary text on dark; page background in light theme (a light tint of Sandal) |
| `--success` | `#8FB996` | Completed state |
| `--error` | `#E5877A` | Error banner and text |

### Theme tokens (`styles/tokens.css`)

```css
:root {
  /* palette */
  --tundora-300: #75696C;
  --tundora-400: #5B4F52;
  --tundora-500: #473D3F;
  --tundora-600: #3A3133;
  --sandal-200:  #D9B693;
  --sandal-300:  #B99271;
  --sandal-400:  #A17858;
  --sandal-500:  #875F43;
  --paper:       #F3E9DD;
  --success:     #8FB996;
  --error:       #E5877A;

  /* dark theme (default) */
  --bg:          var(--tundora-600);
  --surface:     var(--tundora-500);
  --surface-2:   var(--tundora-400);
  --border:      var(--tundora-300);
  --text:        var(--paper);
  --text-muted:  var(--sandal-200);
  --accent:      var(--sandal-200);
  --accent-hover:var(--sandal-300);
  --accent-press:var(--sandal-400);
  --on-accent:   var(--tundora-600);
  --focus-ring:  var(--sandal-200);
}

:root[data-theme="light"] {
  --bg:          var(--paper);
  --surface:     #FFFFFF;
  --surface-2:   #EADBC9;
  --border:      var(--sandal-300);
  --text:        var(--tundora-600);
  --text-muted:  var(--tundora-400);
  --accent:      var(--sandal-500);
  --accent-hover:var(--sandal-400);
  --accent-press:var(--tundora-500);
  --on-accent:   var(--paper);
  --focus-ring:  var(--sandal-500);
}
```

### Color usage rules

| Element | Dark theme | Light theme |
|---|---|---|
| Page background | `--bg` Tundora Dark 01 | `--bg` Paper |
| Cards, inputs | `--surface` Tundora | `--surface` White |
| Primary button | Sandal bg, Tundora Dark text | Sandal Dark 02 bg, Paper text |
| Secondary button | transparent, 1px Sandal border | transparent, 1px Sandal Dark border |
| Progress bar track / fill | `--surface-2` / `--accent` | `--surface-2` / `--accent` |
| Links, logo cursor `_` | Sandal | Sandal Dark 02 |
| Error / success | `--error` / `--success` + icon + text (never color alone) | same |

### Contrast notes (WCAG)
| Pair | Ratio | Allowed for |
|---|---|---|
| Sandal `#D9B693` on Tundora Dark `#3A3133` | ≈ 6.6:1 | All text |
| Paper `#F3E9DD` on Tundora Dark `#3A3133` | > 10:1 | All text |
| Sandal `#B99271` on Tundora Dark `#3A3133` | ≈ 4.4:1 | Large or bold text, icons only |
| Tundora Light 02 `#75696C` on Tundora Dark `#3A3133` | ≈ 2.4:1 | Borders and dividers only, never text |
| Sandal Dark 02 `#875F43` on Paper `#F3E9DD` | ≈ 4.9:1 | All text (light theme) |

### Typography (monospace only)

- **Primary font:** JetBrains Mono, weights 400, 500, 700, 800 (800 is for the logo only).
- **Fallback stack:** `"JetBrains Mono", "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`
- Self-host with `npm i @fontsource/jetbrains-mono` and import weights in `main.tsx`.
- No second font family anywhere (no sans-serif or serif).

| Role | Size / weight | Notes |
|---|---|---|
| Logo | 28px / 800 | letter-spacing `-0.04em` |
| H1 | 24px / 700 | |
| Body, inputs | 16px / 400 | line-height 1.6 |
| Labels, helper text | 13px / 500 | `text-muted` |
| Progress stats (speed, ETA) | 13px / 500 | `font-variant-numeric: tabular-nums` so digits don't jump |

```ts
// tailwind.config.ts (excerpt)
export default {
  theme: {
    fontFamily: {
      mono: ['"JetBrains Mono"', '"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      sans: ['"JetBrains Mono"', 'ui-monospace', 'monospace'], // force mono even for Tailwind's default `font-sans`
    },
    extend: {
      colors: {
        bg: 'var(--bg)', surface: 'var(--surface)', 'surface-2': 'var(--surface-2)',
        border: 'var(--border)', text: 'var(--text)', muted: 'var(--text-muted)',
        accent: 'var(--accent)', 'on-accent': 'var(--on-accent)',
      },
      borderRadius: { DEFAULT: '6px' },
    },
  },
}
```

### Logo: font-based `YTD_` wordmark

- It is **live text**, not an image, set in JetBrains Mono ExtraBold. `YTD` takes the text color and the trailing `_` (a terminal cursor) takes the accent color.
- The cursor can blink slowly (1.1s step animation); disable it under `prefers-reduced-motion`.
- Minimum size 20px. Keep clear space equal to the width of one character around it. Never stretch, outline, or add effects.
- Favicon is `Y_` as an SVG text mark: Sandal on a Tundora Dark rounded square.

```tsx
// components/Logo.tsx
export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span
      role="img"
      aria-label="YTD"
      className="font-mono font-extrabold tracking-tighter select-none text-text"
      style={{ fontSize: size, lineHeight: 1 }}
    >
      YTD<span className="text-accent ytd-cursor" aria-hidden="true">_</span>
    </span>
  );
}
```

```css
/* index.css */
.ytd-cursor { animation: ytd-blink 1.1s steps(1) infinite; }
@keyframes ytd-blink { 50% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .ytd-cursor { animation: none; } }
```

```svg
<!-- public/favicon.svg -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" fill="#3A3133"/>
  <text x="32" y="44" text-anchor="middle"
        font-family="JetBrains Mono, ui-monospace, monospace"
        font-weight="800" font-size="34" fill="#D9B693">Y_</text>
</svg>
```

### Header layout
`Logo` on the left, theme toggle on the right, 1px bottom border in `--border`. Under the logo, one muted line in monospace: `paste a url. get a file.`

---

## 8. Security Design
- Allow-list hosts: `youtube.com`, `www.youtube.com`, `m.youtube.com`, `youtu.be`. Reject everything else (prevents SSRF).
- Pydantic validation on every request body.
- Rate limit (e.g., 10 requests/min/IP via `slowapi`).
- CORS restricted to configured origins.
- Disable yt-dlp features that execute external commands; use fixed, server-defined options only.
- Job IDs are random UUIDs; files are served only for known job IDs (no path input from the client).
- Run the container as a non-root user.

## 9. Testing Strategy
| Level | Tools | Coverage |
|---|---|---|
| Backend unit | pytest | URL validator, filename sanitizer, job state transitions |
| Backend integration | pytest + httpx + mocked yt-dlp | API endpoints, SSE stream |
| Frontend unit | Vitest + Testing Library | Form validation, picker, progress rendering |
| E2E (optional) | Playwright | Paste → preview → download with a mocked backend |

## 10. Deployment
- `docker-compose.yml` with two services: `backend` (python:3.12-slim + ffmpeg) and `frontend` (Vite build served by nginx, proxying `/api`).
- Volumes: ephemeral download dir (tmpfs or named volume).
- CI: GitHub Actions running lint (ruff, eslint), tests, and image build.
