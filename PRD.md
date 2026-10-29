# YouTube Downloader (YTD) — PRD

**Document:** Product Requirements Document
**Stack:** React (Vite + TypeScript) frontend · Python (FastAPI + yt-dlp + ffmpeg) backend
**Brand:** Font-based `YTD_` logo · monospace type · Tundora + Sandal palette
**Status:** Draft v1.1
**Related:** `DESIGN.md` (architecture, API, UI, brand) · `AGENT.md` (coding-agent instructions)

> **Assumptions:** single-user / self-hosted tool, no login in v1, runs locally or in Docker.
>
> **Legal note:** Downloading from YouTube may violate its Terms of Service unless the content is yours, Creative Commons / public domain, or you have permission. The app should show this notice and is intended for personal, lawful use.

---

## 1. Overview
A web app where a user pastes a YouTube URL, previews the video details, picks a format and quality, and downloads the file. The React UI shows live progress; the Python backend does the fetching and conversion.

## 2. Goals
- Paste a URL and get a downloadable file in under 4 clicks.
- Support video (MP4) and audio-only (MP3 / M4A).
- Show real-time progress, speed, and ETA.
- Be simple to run locally (`docker compose up`).

## 3. Non-Goals (v1)
- User accounts, payments, or cloud storage.
- Downloading private, age-restricted, or DRM-protected content.
- Mobile native apps.
- Bulk scraping of channels.

## 4. Target Users
| Persona | Need |
|---|---|
| Student / learner | Save lectures offline |
| Creator | Download own uploads or CC-licensed clips |
| Developer | Self-host a clean, hackable downloader |

## 5. User Stories
1. As a user, I paste a URL so I can see the title, thumbnail, duration, and channel.
2. As a user, I choose video quality (144p–4K where available) or audio-only.
3. As a user, I see a progress bar with speed and ETA.
4. As a user, I download the finished file with a clean filename.
5. As a user, I can preview a playlist, choose which videos to keep, and download
   the selected videos as one ZIP (Phase 2).
6. As a user, I see clear errors (invalid URL, unavailable, region-blocked).

## 6. Functional Requirements
| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Validate that the input is a YouTube URL (`youtube.com`, `youtu.be`, `m.youtube.com`) | P0 |
| FR-2 | Fetch metadata (title, thumbnail, duration, channel, available formats) | P0 |
| FR-3 | Download selected format; merge video+audio with ffmpeg | P0 |
| FR-4 | Audio extraction to MP3 / M4A | P0 |
| FR-5 | Real-time progress via SSE | P0 |
| FR-6 | Serve the finished file; auto-delete after TTL (default 30 min) | P0 |
| FR-7 | Cancel a running job | P1 |
| FR-8 | Download history (in-browser, localStorage) | P1 |
| FR-9 | Subtitles download (SRT / VTT) | P1 |
| FR-10 | Playlist support (per-video selection, quality cap, ZIP output) | P2 |
| FR-11 | Light/dark theme (both built from the Tundora + Sandal palette) | P2 |
| FR-12 | Font-based `YTD_` wordmark logo in the header and as favicon; all UI text in monospace | P0 |

## 7. Non-Functional Requirements
- **Performance:** Metadata response under 3 s (p95); UI never blocks on downloads.
- **Reliability:** Failed jobs show a readable error; no orphaned temp files.
- **Security:** Strict URL allow-list, no shell execution, rate limiting, CORS locked to the frontend origin.
- **Compatibility:** Latest Chrome, Edge, Firefox, Safari.
- **Accessibility:** WCAG 2.1 AA basics (labels, focus states, contrast). Only the approved text/background pairs in `DESIGN.md` (Brand & Visual Identity) may be used.
- **Brand consistency:** Colors come only from the design tokens; fonts only from the mono stack.
- **Maintainability:** `yt-dlp` pinned and easy to upgrade (YouTube changes often).

## 8. Success Metrics
- ≥ 95% of valid public URLs download successfully.
- Time from paste to download start < 10 s.
- Zero leftover temp files after TTL cleanup.

## 9. Risks & Mitigations
| Risk | Mitigation |
|---|---|
| YouTube changes break extraction | Pin and regularly upgrade `yt-dlp`; health-check endpoint reports version |
| ToS / legal exposure | Disclaimer in UI, personal-use framing, no hosted public service |
| Abuse of a public deployment | Rate limit per IP, max duration/size caps |
| Disk fills up | TTL cleanup job, max concurrent jobs, size cap |

## 10. Milestones
| Phase | Scope |
|---|---|
| M1 | Backend: info + download + file serve; CLI-testable |
| M2 | React UI: URL form, preview card, format picker |
| M3 | SSE progress, cancel, error handling |
| M4 | Docker, tests, README |
| M5 | Playlists, subtitles, history |
