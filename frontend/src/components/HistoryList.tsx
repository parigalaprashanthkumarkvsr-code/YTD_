import { jobFileUrl } from "../api/client";
import type { HistoryEntry } from "../hooks/useHistory";
import { formatHistoryDate } from "../lib/format";

interface HistoryListProps {
  entries: HistoryEntry[];
  onClear: () => void;
}

export function HistoryList({ entries, onClear }: HistoryListProps) {
  if (entries.length === 0) {
    return null;
  }

  return (
    <section
      aria-labelledby="history-heading"
      className="rounded-md border border-border bg-surface p-4 sm:p-5"
    >
      <div className="flex items-center justify-between gap-3">
        <h2 id="history-heading" className="text-label font-bold uppercase tracking-wide">
          history
        </h2>
        <button
          type="button"
          onClick={onClear}
          className="text-label text-muted underline decoration-border underline-offset-4 transition-colors hover:text-text"
        >
          clear
        </button>
      </div>

      <ul className="mt-3 divide-y divide-border">
        {entries.map((entry) => {
          return (
            <li key={entry.jobId} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
              <div className="min-w-0 flex-1">
                <p className="truncate text-[16px] font-medium" title={entry.title}>
                  {entry.title}
                </p>
                <p className="truncate text-label text-muted">
                  {entry.label} · {formatHistoryDate(entry.completedAt)}
                </p>
              </div>
              <a
                href={jobFileUrl(entry.jobId)}
                download={entry.filename}
                className="shrink-0 rounded border border-accent px-3 py-1.5 text-label font-medium text-text transition-colors hover:bg-surface-2"
              >
                save
              </a>
            </li>
          );
        })}
      </ul>

      <p className="mt-3 text-label text-muted">
        stored in this browser · files are cleaned up automatically
      </p>
    </section>
  );
}
