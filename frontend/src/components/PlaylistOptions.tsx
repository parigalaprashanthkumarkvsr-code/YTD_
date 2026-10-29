import type { AudioFormat, DownloadKind, PlaylistQuality } from "../types";

interface PlaylistOptionsProps {
  kind: DownloadKind;
  onKindChange: (kind: DownloadKind) => void;
  quality: PlaylistQuality | null;
  onQualityChange: (quality: PlaylistQuality | null) => void;
  audioFormat: AudioFormat;
  onAudioFormatChange: (format: AudioFormat) => void;
  videoCount: number;
}

interface OptionCardProps {
  name: string;
  checked: boolean;
  onSelect: () => void;
  title: string;
  description: string;
}

const VIDEO_QUALITIES: Array<{
  value: PlaylistQuality | null;
  title: string;
  description: string;
}> = [
  {
    value: null,
    title: "Best available",
    description: "highest quality for each video",
  },
  {
    value: 2160,
    title: "2160p or lower",
    description: "4K when available",
  },
  {
    value: 1440,
    title: "1440p or lower",
    description: "2K when available",
  },
  {
    value: 1080,
    title: "1080p or lower",
    description: "full HD when available",
  },
  {
    value: 720,
    title: "720p or lower",
    description: "smaller files",
  },
  {
    value: 480,
    title: "480p or lower",
    description: "smallest video files",
  },
  {
    value: 360,
    title: "360p or lower",
    description: "low bandwidth",
  },
];

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

export function PlaylistOptions({
  kind,
  onKindChange,
  quality,
  onQualityChange,
  audioFormat,
  onAudioFormatChange,
  videoCount,
}: PlaylistOptionsProps) {
  return (
    <section aria-label="Playlist download options" className="space-y-4">
      <p className="text-label text-muted">
        {videoCount} {videoCount === 1 ? "video" : "videos"} · the finished files are
        bundled into one ZIP
      </p>

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
            id={`playlist-tab-${tab}`}
            aria-selected={kind === tab}
            aria-controls={`playlist-panel-${tab}`}
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
          id="playlist-panel-video"
          aria-labelledby="playlist-tab-video"
          tabIndex={0}
          className="space-y-2"
        >
          {VIDEO_QUALITIES.map((option) => (
            <OptionCard
              key={option.value ?? "best"}
              name="playlist-quality"
              checked={quality === option.value}
              onSelect={() => onQualityChange(option.value)}
              title={option.title}
              description={option.description}
            />
          ))}
        </div>
      ) : (
        <div
          role="tabpanel"
          id="playlist-panel-audio"
          aria-labelledby="playlist-tab-audio"
          tabIndex={0}
          className="space-y-2"
        >
          <OptionCard
            name="playlist-audio-format"
            checked={audioFormat === "mp3"}
            onSelect={() => onAudioFormatChange("mp3")}
            title="MP3 · 192 kbps"
            description="smaller files · plays everywhere"
          />
          <OptionCard
            name="playlist-audio-format"
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
