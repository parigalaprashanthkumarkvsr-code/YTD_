interface ErrorBannerProps {
  message: string;
  code?: string;
  title?: string;
  tone?: "error" | "muted";
  onRetry?: () => void;
  retryLabel?: string;
}

export function ErrorBanner({
  message,
  code,
  title = "error",
  tone = "error",
  onRetry,
  retryLabel = "retry",
}: ErrorBannerProps) {
  const errorTone = tone === "error";

  return (
    <div
      role="alert"
      className={`flex flex-col gap-3 rounded-md border bg-surface p-4 sm:flex-row sm:items-start ${
        errorTone ? "border-error" : "border-border"
      }`}
    >
      <svg
        aria-hidden="true"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={`mt-0.5 shrink-0 ${errorTone ? "text-text" : "text-muted"}`}
      >
        {errorTone ? (
          <>
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7.5v5.5M12 16.5h.01" />
          </>
        ) : (
          <>
            <circle cx="12" cy="12" r="9" />
            <path d="M8.5 12h7" />
          </>
        )}
      </svg>

      <div className="min-w-0 flex-1">
        <p
          className={`text-label font-bold uppercase tracking-wide ${
            errorTone ? "text-text" : "text-muted"
          }`}
        >
          {title}
        </p>
        <p className="mt-0.5 break-words text-[16px]">{message}</p>
        {code ? <p className="mt-1 text-label text-muted">code: {code}</p> : null}
      </div>

      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="shrink-0 self-start rounded border border-accent bg-transparent px-3 py-1.5 text-label font-medium text-text transition-colors hover:bg-surface-2"
        >
          {retryLabel}
        </button>
      ) : null}
    </div>
  );
}
