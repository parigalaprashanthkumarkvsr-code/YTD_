import { useId, useState } from "react";
import type { FormEvent } from "react";

import { isYouTubeUrl, parseYouTubeUrl } from "../lib/url";

interface UrlFormProps {
  onSubmit: (url: string) => void;
  busy?: boolean;
}

export function UrlForm({ onSubmit, busy = false }: UrlFormProps) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputId = useId();
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;

  const trimmed = value.trim();
  const detected = parseYouTubeUrl(trimmed);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }
    if (!trimmed) {
      setError("Paste a YouTube link first.");
      return;
    }
    if (!isYouTubeUrl(trimmed)) {
      setError("That doesn't look like a YouTube video or playlist link.");
      return;
    }
    setError(null);
    onSubmit(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <label htmlFor={inputId} className="sr-only">
        YouTube URL
      </label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative min-w-0 flex-1">
          <span
            aria-hidden="true"
            className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-accent"
          >
            &gt;
          </span>
          <input
            id={inputId}
            name="url"
            type="url"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            value={value}
            onChange={(event) => {
              setValue(event.target.value);
              if (error) {
                setError(null);
              }
            }}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? `${hintId} ${errorId}` : hintId}
            placeholder="https://youtube.com/watch?v=... or /playlist?list=..."
            className="h-12 w-full rounded border border-border bg-surface pl-9 pr-4 text-text transition-colors placeholder:text-muted hover:border-muted focus:border-accent"
          />
        </div>
        <button
          type="submit"
          disabled={busy}
          className="inline-flex h-12 shrink-0 items-center justify-center gap-2 rounded bg-accent px-6 font-bold text-on-accent transition-colors hover:bg-accent-hover active:bg-accent-press disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? "Fetching" : "Fetch"}
          <span aria-hidden="true">{busy ? "..." : "->"}</span>
        </button>
      </div>

      <div className="mt-2 min-h-6 text-label">
        {error ? (
          <p id={errorId} role="alert" className="text-error">
            {error}
          </p>
        ) : detected ? (
          <p id={hintId} className="text-muted">
            <span className="text-accent" aria-hidden="true">
              [ok]
            </span>{" "}
            link detected · {detected.kind === "playlist" ? "playlist " : ""}
            {detected.id}
          </p>
        ) : (
          <p id={hintId} className="text-muted">
            youtube.com · youtu.be · shorts · live · playlists
          </p>
        )}
      </div>
    </form>
  );
}
