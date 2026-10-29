# AGENT.md — YouTube Downloader (YTD)

> Place this file at the repo root (or rename to `AGENTS.md` / `CLAUDE.md`) so Claude Code or any coding agent follows it.
> Source-of-truth docs: `PRD.md` (what to build) and `DESIGN.md` (how to build it and how it looks). Keep all three in the repo root or `/docs`.

---

## Role
You are a senior full-stack engineer building a YouTube downloader. Backend is Python (FastAPI + yt-dlp). Frontend is React + TypeScript (Vite). Follow `PRD.md` and `DESIGN.md` as the source of truth.

## Ground Rules
1. **Read before writing.** Check existing files, then make the smallest change that satisfies the task.
2. **Work in milestones** (M1 → M5 in `PRD.md`). Finish and test one before starting the next.
3. **Never run yt-dlp via shell strings** (`os.system`, `subprocess` with `shell=True`). Use the `yt_dlp` Python API only.
4. **Validate all input** with Pydantic; enforce the YouTube host allow-list.
5. **Type everything:** Python type hints, strict TypeScript (`"strict": true`), no `any`.
6. **No secrets in code.** Use env vars and a `.env.example`.
7. **Ask before** adding a dependency not listed in the Tech Choices table of `DESIGN.md`, changing the API contract, or deleting files.
8. **Don't add features** outside the PRD scope (no auth, no cloud storage) unless asked.
9. **Follow the Brand & Visual Identity section of `DESIGN.md` exactly:** colors only via the CSS variables in `tokens.css` (no raw hex in components), monospace fonts only, and the logo only through `<Logo />`.

## Coding Standards
**Python**
- Python 3.12, FastAPI, Pydantic v2, `ruff` + `black`, `pytest`.
- Async endpoints; blocking work goes through `asyncio.to_thread`.
- Raise typed exceptions from `core/errors.py`; one global handler returns the JSON error format.
- Log with the `logging` module (structured, no print).

**React / TypeScript**
- Function components + hooks only; one component per file.
- Server state via TanStack Query; local UI state via `useState`/`useReducer`.
- Tailwind for styling; no inline style objects except dynamic values (e.g., progress width, logo size).
- Never hard-code colors or font families in components; use the token-mapped Tailwind classes (`bg-bg`, `text-muted`, `bg-accent`, `font-mono`).
- Respect `prefers-reduced-motion` for the blinking logo cursor and any animation.
- All API calls go through `src/api/client.ts`.
- Use `EventSource` for progress and always close it in a cleanup function.

## Definition of Done (per task)
- [ ] Code compiles/lints cleanly (`ruff check`, `eslint`, `tsc --noEmit`)
- [ ] Tests added or updated and passing (`pytest`, `vitest`)
- [ ] API changes reflected in `DESIGN.md` and the OpenAPI docs
- [ ] Error and loading states handled in the UI
- [ ] UI uses only the Tundora + Sandal tokens and the mono font stack; text pairs pass the contrast table
- [ ] No temp files left behind after a job finishes, fails, or is cancelled
- [ ] README updated if setup steps changed

## Commands
```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest -q
ruff check . && black --check .

# Frontend
cd frontend && npm install
npm run dev          # http://localhost:5173 (proxies /api → :8000)
npm run test
npm run lint && npx tsc --noEmit

# Full stack
docker compose up --build
```

## Starter Prompts (use in order)

**Prompt 1 — Backend skeleton (M1)**
```
Create the backend per `DESIGN.md`: FastAPI app, config via pydantic-settings,
URL validator with the YouTube host allow-list, POST /api/info using the yt_dlp
Python API (download=False), and GET /api/health. Add pytest tests for the validator
and for /info with yt-dlp mocked. Don't build downloads yet.
```

**Prompt 2 — Download jobs (M1)**
```
Add POST /api/downloads, GET /api/downloads/{id}, and GET /api/downloads/{id}/file.
Use a job manager with asyncio.to_thread and a yt-dlp progress hook. Support
kind=video (merge best video+audio into MP4) and kind=audio (mp3/m4a via ffmpeg).
Each job writes to DOWNLOAD_DIR/<job_id>/. Add TTL cleanup. Include tests.
```

**Prompt 3 — SSE progress + cancel (M3)**
```
Add GET /api/downloads/{id}/events (SSE) streaming JSON progress, and
DELETE /api/downloads/{id} to cancel and delete files. Make sure the SSE stream
ends cleanly on done/error/cancelled.
```

**Prompt 4 — React UI (M2/M3)**
```
Scaffold the Vite + React + TS + Tailwind frontend per `DESIGN.md` structure.
Apply the Brand & Visual Identity section of DESIGN.md: create styles/tokens.css with the Tundora + Sandal variables
(dark default, light via data-theme), install @fontsource/jetbrains-mono and set the
mono font stack in tailwind.config.ts, and build the font-based Logo.tsx (YTD_ with
a blinking accent cursor) plus public/favicon.svg.
Build Logo, UrlForm, VideoCard, FormatPicker, ProgressBar, ErrorBanner, LegalNotice.
Wire useVideoInfo and useDownload (with EventSource). Handle empty, loading,
error, progress, and success states. Add Vitest tests for UrlForm and FormatPicker.
```

**Prompt 5 — Docker & polish (M4)**
```
Add Dockerfiles (backend with ffmpeg, frontend built and served by nginx),
docker-compose.yml, .env.example, a README with setup and the legal notice, and a
GitHub Actions workflow for lint + tests.
```

## Guardrails for Bugs
- If a download fails, first check the `yt-dlp` version (`pip install -U yt-dlp`); most breakages come from YouTube-side changes.
- Reproduce with a failing test or a minimal script before changing code.
- Fix the root cause; don't wrap failures in broad `except Exception: pass`.

## Out of Scope Reminder
Do not implement bypassing of DRM, age or region restrictions, login/cookie extraction, or bulk channel scraping. Keep the UI legal notice visible.
