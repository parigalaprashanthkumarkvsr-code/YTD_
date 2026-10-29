import { useState } from "react";

import { formatDuration } from "../lib/format";
import type { PlaylistItem } from "../types";

interface PlaylistItemListProps {
  items: PlaylistItem[];
  selectedIds: string[];
  onToggle: (videoId: string) => void;
  onSelectAll: () => void;
  onClear: () => void;
}

interface PlaylistRowProps {
  item: PlaylistItem;
  index: number;
  checked: boolean;
  onToggle: (videoId: string) => void;
}

function PlaylistRow({ item, index, checked, onToggle }: PlaylistRowProps) {
  const [thumbnailFailed, setThumbnailFailed] = useState(false);
  const showThumbnail = Boolean(item.thumbnail) && !thumbnailFailed;

  return (
    <li>
      <label
        className={`relative flex cursor-pointer items-center gap-3 px-4 py-3 transition-colors focus-within:ring-2 focus-within:ring-accent ${
          checked ? "bg-surface-2" : "hover:bg-surface-2"
        }`}
      >
        <input
          type="checkbox"
          checked={checked}
          onChange={() => onToggle(item.id)}
          className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0 focus:outline-none"
        />
        <span
          aria-hidden="true"
          className={`pointer-events-none flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border ${
            checked ? "border-accent bg-accent text-on-accent" : "border-muted"
          }`}
        >
          {checked ? (
            <svg
              width="10"
              height="10"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m4 12 5 5L20 6" />
            </svg>
          ) : null}
        </span>

        <span className="relative hidden h-10 w-16 shrink-0 overflow-hidden rounded bg-surface-2 sm:block">
          {showThumbnail ? (
            <img
              src={item.thumbnail ?? ""}
              alt=""
              loading="lazy"
              referrerPolicy="no-referrer"
              className="h-full w-full object-cover"
              onError={() => setThumbnailFailed(true)}
            />
          ) : (
            <span className="flex h-full w-full items-center justify-center text-label text-muted">
              {String(index + 1).padStart(2, "0")}
            </span>
          )}
        </span>

        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium" title={item.title}>
            {item.title}
          </span>
          <span className="mt-0.5 block text-label text-muted">
            video {index + 1} · {formatDuration(item.duration)}
          </span>
        </span>
      </label>
    </li>
  );
}

export function PlaylistItemList({
  items,
  selectedIds,
  onToggle,
  onSelectAll,
  onClear,
}: PlaylistItemListProps) {
  if (items.length === 0) {
    return null;
  }

  const selected = new Set(selectedIds);
  const allSelected = selectedIds.length === items.length;

  return (
    <section
      aria-labelledby="playlist-items-heading"
      className="overflow-hidden rounded-md border border-border bg-surface"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div>
          <h2
            id="playlist-items-heading"
            className="text-label font-bold uppercase tracking-wide"
          >
            videos in playlist
          </h2>
          <p className="mt-0.5 text-label text-muted" aria-live="polite">
            {selectedIds.length} of {items.length} selected
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onSelectAll}
            disabled={allSelected}
            className="text-label text-accent underline decoration-border underline-offset-4 transition-colors hover:text-accent-hover disabled:cursor-not-allowed disabled:text-muted disabled:no-underline"
          >
            select all
          </button>
          <button
            type="button"
            onClick={onClear}
            disabled={selectedIds.length === 0}
            className="text-label text-muted underline decoration-border underline-offset-4 transition-colors hover:text-text disabled:cursor-not-allowed disabled:no-underline disabled:opacity-60"
          >
            clear
          </button>
        </div>
      </div>

      <ul className="max-h-96 divide-y divide-border overflow-y-auto">
        {items.map((item, index) => (
          <PlaylistRow
            key={item.id}
            item={item}
            index={index}
            checked={selected.has(item.id)}
            onToggle={onToggle}
          />
        ))}
      </ul>
    </section>
  );
}
