const ALLOWED_HOSTS = new Set(["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"]);
const VIDEO_ID_RE = /^[A-Za-z0-9_-]{6,20}$/;
const PLAYLIST_ID_RE = /^[A-Za-z0-9_-]{10,64}$/;

export type YouTubeTarget =
  | { kind: "video"; id: string }
  | { kind: "playlist"; id: string };

function parseCandidate(raw: string): URL | null {
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }
  const withScheme = trimmed.includes("://") ? trimmed : `https://${trimmed}`;
  try {
    return new URL(withScheme);
  } catch {
    return null;
  }
}

export function parseYouTubeUrl(raw: string): YouTubeTarget | null {
  const url = parseCandidate(raw);
  if (!url) {
    return null;
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") {
    return null;
  }
  if (url.username || url.password || url.port) {
    return null;
  }

  const host = url.hostname.toLowerCase().replace(/\.$/, "");
  if (!ALLOWED_HOSTS.has(host)) {
    return null;
  }

  const path = url.pathname.replace(/\/+$/, "");

  if (path === "/playlist") {
    const playlistId = url.searchParams.get("list");
    return playlistId && PLAYLIST_ID_RE.test(playlistId)
      ? { kind: "playlist", id: playlistId }
      : null;
  }

  let candidate: string | null = null;
  if (host === "youtu.be") {
    const segments = path.split("/").filter(Boolean);
    candidate = segments.length === 1 ? (segments[0] ?? null) : null;
  } else if (path === "/watch") {
    candidate = url.searchParams.get("v");
  } else {
    const match = path.match(/^\/(?:shorts|live|embed|v)\/([^/]+)$/);
    candidate = match?.[1] ?? null;
  }

  return candidate && VIDEO_ID_RE.test(candidate)
    ? { kind: "video", id: candidate }
    : null;
}

export function extractYouTubeId(raw: string): string | null {
  const target = parseYouTubeUrl(raw);
  return target?.kind === "video" ? target.id : null;
}

export function extractYouTubePlaylistId(raw: string): string | null {
  const target = parseYouTubeUrl(raw);
  return target?.kind === "playlist" ? target.id : null;
}

export function isYouTubeUrl(raw: string): boolean {
  return parseYouTubeUrl(raw) !== null;
}
