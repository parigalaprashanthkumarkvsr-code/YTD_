export function SkeletonCard() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="animate-pulse overflow-hidden rounded-md border border-border bg-surface"
    >
      <span className="sr-only">Fetching video details...</span>
      <div aria-hidden="true" className="aspect-video w-full bg-surface-2" />
      <div aria-hidden="true" className="space-y-3 p-4 sm:p-5">
        <div className="h-4 w-4/5 rounded bg-surface-2" />
        <div className="h-3 w-2/5 rounded bg-surface-2" />
      </div>
    </div>
  );
}
