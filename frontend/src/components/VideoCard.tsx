import { useState } from "react";

import { formatDuration } from "../lib/format";
import type { MediaInfo } from "../types";
import { Logo } from "./Logo";

interface VideoCardProps {
  info: MediaInfo;
}

export function VideoCard({ info }: VideoCardProps) {
  const [thumbnailFailed, setThumbnailFailed] = useState(false);
  const showThumbnail = Boolean(info.thumbnail) && !thumbnailFailed;
  const isPlaylist = info.kind === "playlist";
  const sourceUrl = isPlaylist
    ? `https://www.youtube.com/playlist?list=${encodeURIComponent(info.id)}`
    : `https://www.youtube.com/watch?v=${encodeURIComponent(info.id)}`;

  return (
    <article className="overflow-hidden rounded-md border border-border bg-surface">
      <div className="relative aspect-video w-full bg-surface-2">
        {showThumbnail ? (
          <img
            src={info.thumbnail ?? ""}
            alt={`Thumbnail for ${info.title}`}
            className="h-full w-full object-cover"
            referrerPolicy="no-referrer"
            onError={() => setThumbnailFailed(true)}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Logo size={22} />
          </div>
        )}
        {isPlaylist ? (
          <span className="absolute left-3 top-3 rounded border border-border bg-bg px-2 py-0.5 text-label font-bold uppercase tracking-wide">
            playlist
          </span>
        ) : null}
        <span className="absolute bottom-3 right-3 rounded border border-border bg-bg px-2 py-0.5 text-label tabular-nums">
          {isPlaylist ? `${info.video_count} videos` : formatDuration(info.duration)}
        </span>
      </div>
      <div className="space-y-1 p-4 sm:p-5">
        <h2 className="line-clamp-2 text-[18px] font-bold leading-snug">{info.title}</h2>
        <p className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-label text-muted">
          <span>{info.channel}</span>
          <span aria-hidden="true">/</span>
          <a
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
            className="underline decoration-border underline-offset-4 transition-colors hover:text-accent"
          >
            youtube.com
          </a>
        </p>
      </div>
    </article>
  );
}
