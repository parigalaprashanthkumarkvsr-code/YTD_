export function LegalNotice() {
  return (
    <p className="text-label leading-relaxed text-muted">
      Downloading from YouTube may violate its{" "}
      <a
        href="https://www.youtube.com/t/terms"
        target="_blank"
        rel="noreferrer"
        className="underline decoration-border underline-offset-4 transition-colors hover:text-accent"
      >
        Terms of Service
      </a>{" "}
      unless the content is yours, Creative Commons / public domain, or you have permission.
      YTD is intended for personal, lawful use only.
    </p>
  );
}
