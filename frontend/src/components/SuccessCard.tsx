import { jobFileUrl } from "../api/client";
import type { JobState } from "../types";

interface SuccessCardProps {
  job: JobState;
  onAnother: () => void;
}

export function SuccessCard({ job, onAnother }: SuccessCardProps) {
  const playlist = job.playlist;
  const saved = playlist
    ? Math.max(0, playlist.total_items - playlist.skipped_items)
    : 0;

  return (
    <section
      role="status"
      className="space-y-4 rounded-md border border-success bg-surface p-4 sm:p-5"
    >
      <div className="flex items-start gap-3">
        <svg
          aria-hidden="true"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="mt-0.5 shrink-0 text-text"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="m8.2 12.2 2.5 2.5 5.1-5.4" />
        </svg>
        <div className="min-w-0 flex-1">
          <h2 className="text-label font-bold uppercase tracking-wide text-text">
            {playlist ? "playlist complete" : "download complete"}
          </h2>
          <p className="mt-1 break-words text-[16px]" title={job.filename ?? undefined}>
            {job.filename ?? "your file is ready"}
          </p>
          {playlist ? (
            <p className="mt-1 text-label text-muted">
              {saved} of {playlist.total_items}{" "}
              {playlist.total_items === 1 ? "video" : "videos"} saved
              {playlist.skipped_items > 0
                ? ` · ${playlist.skipped_items} skipped`
                : ""}
            </p>
          ) : null}
        </div>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <a
          href={jobFileUrl(job.id)}
          download={job.filename ?? undefined}
          className="inline-flex h-11 flex-1 items-center justify-center rounded bg-accent px-5 font-bold text-on-accent transition-colors hover:bg-accent-hover active:bg-accent-press"
        >
          {playlist ? "Save ZIP" : "Save file"}
        </a>
        <button
          type="button"
          onClick={onAnother}
          className="inline-flex h-11 flex-1 items-center justify-center rounded border border-accent bg-transparent px-5 font-medium text-text transition-colors hover:bg-surface-2"
        >
          Download another
        </button>
      </div>
    </section>
  );
}
