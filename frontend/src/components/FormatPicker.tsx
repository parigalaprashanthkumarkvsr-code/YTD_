import { formatBytes } from "../lib/format";
import type { AudioFormat, DownloadKind, VideoFormat } from "../types";

interface FormatPickerProps {
  formats: VideoFormat[];
  kind: DownloadKind;
  onKindChange: (kind: DownloadKind) => void;
  selectedFormatId: string | null;
  onFormatChange: (formatId: string) => void;
  audioFormat: AudioFormat;
  onAudioFormatChange: (format: AudioFormat) => void;
}

interface OptionCardProps {
  name: string;
  checked: boolean;
  onSelect: () => void;
  title: string;
  description: string;
}

function OptionCard({ name, checked, onSelect, title, description }: OptionCardProps) {
  return (
    <label
      className={`flex cursor-pointer items-center gap-3 rounded border px-4 py-3 transition-colors focus-within:ring-2 focus-within:ring-accent ${
        checked
          ? "border-accent bg-surface-2"
          : "border-border bg-surface hover:border-muted"
      }`}
    >
      <input
        type="radio"
        name={name}
        checked={checked}
        onChange={onSelect}
        className="peer sr-only"
      />
      <span
        aria-hidden="true"
        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
          checked ? "border-accent" : "border-muted"
        }`}
      >
        {checked ? <span className="h-2 w-2 rounded-full bg-accent" /> : null}
      </span>
      <span className="min-w-0">
        <span className="block font-medium">{title}</span>
        <span className="block text-label text-muted">{description}</span>
      </span>
    </label>
  );
}

export function FormatPicker({
  formats,
  kind,
  onKindChange,
  selectedFormatId,
  onFormatChange,
  audioFormat,
  onAudioFormatChange,
}: FormatPickerProps) {
  const videoFormats = formats
    .filter((format) => format.height !== null)
    .slice()
    .sort((a, b) => (b.height ?? 0) - (a.height ?? 0));

  return (
    <section aria-label="Download options" className="space-y-4">
      <div
        role="tablist"
        aria-label="Download type"
        className="flex gap-1 rounded bg-surface-2 p-1"
      >
        {(["video", "audio"] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            id={`tab-${tab}`}
            aria-selected={kind === tab}
            aria-controls={`panel-${tab}`}
            onClick={() => onKindChange(tab)}
            className={`flex-1 rounded px-4 py-2 text-label font-bold uppercase tracking-wide transition-colors ${
              kind === tab
                ? "bg-accent text-on-accent"
                : "text-muted hover:text-text"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {kind === "video" ? (
        <div
          role="tabpanel"
          id="panel-video"
          aria-labelledby="tab-video"
          tabIndex={0}
          className="space-y-2"
        >
          {videoFormats.length === 0 ? (
            <p className="rounded border border-border bg-surface p-4 text-label text-muted">
              No video formats were found. Try the audio tab instead.
            </p>
          ) : (
            videoFormats.map((format) => (
              <OptionCard
                key={format.format_id}
                name="video-format"
                checked={selectedFormatId === format.format_id}
                onSelect={() => onFormatChange(format.format_id)}
                title={format.label}
                description={formatBytes(format.filesize)}
              />
            ))
          )}
        </div>
      ) : (
        <div
          role="tabpanel"
          id="panel-audio"
          aria-labelledby="tab-audio"
          tabIndex={0}
          className="space-y-2"
        >
          <OptionCard
            name="audio-format"
            checked={audioFormat === "mp3"}
            onSelect={() => onAudioFormatChange("mp3")}
            title="MP3 · 192 kbps"
            description="smaller files · plays everywhere"
          />
          <OptionCard
            name="audio-format"
            checked={audioFormat === "m4a"}
            onSelect={() => onAudioFormatChange("m4a")}
            title="M4A · original audio"
            description="AAC audio · no quality loss"
          />
        </div>
      )}
    </section>
  );
}
