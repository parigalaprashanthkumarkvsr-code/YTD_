import { formatEta, statusLabel } from "../lib/format";
import type { JobState } from "../types";

interface ProgressBarProps {
  job: JobState;
  onCancel: () => void;
}

export function ProgressBar({ job, onCancel }: ProgressBarProps) {
  const percent = Math.max(0, Math.min(100, job.percent));
  const eta = formatEta(job.eta);
  const active = job.status === "queued" || job.status === "downloading" || job.status === "processing";

  return (
    <section
      aria-label="Download progress"
      className="space-y-4 rounded-md border border-border bg-surface p-4 sm:p-5"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className={`h-2 w-2 rounded-full ${
              job.status === "processing" ? "bg-success" : "bg-accent"
            }`}
          />
          <span className="text-label font-bold uppercase tracking-wide" aria-live="polite">
            {statusLabel(job.status)}
          </span>        </div>
        <span className="text-label tabular-nums text-muted">{percent.toFixed(0)}%</span>
      </div>

      <div
        role="progressbar"
        aria-label="Download progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        className="h-2 overflow-hidden rounded bg-surface-2"
      >
        <div
          className="h-full rounded bg-accent transition-[width] duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>

      {job.playlist && job.playlist.total_items > 0 ? (
        <p
          className="truncate text-label text-muted"
          title={job.playlist.current_title ?? undefined}
        >
          video {job.playlist.current_item ?? job.playlist.completed_items} of{" "}
          {job.playlist.total_items}
          {job.playlist.current_title ? ` · ${job.playlist.current_title}` : ""}
          {job.playlist.skipped_items > 0
            ? ` · ${job.playlist.skipped_items} skipped`
            : ""}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-label text-muted" aria-live="polite">
          {job.status === "queued" ? (
            "waiting for a slot"
          ) : (
            <span className="tabular-nums">
              {job.status === "processing" ? "processing" : (job.speed ?? "downloading")}
              {eta ? ` · ${eta} left` : ""}
            </span>
          )}
        </p>
        {active ? (
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-border bg-transparent px-3 py-1.5 text-label font-medium text-text transition-colors hover:border-error"
          >
            Cancel
          </button>
        ) : null}
      </div>
    </section>
  );
}
