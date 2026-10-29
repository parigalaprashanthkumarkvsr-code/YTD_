import type { VideoFormat } from "../types";

export function pickDefaultFormat(
  formats: VideoFormat[],
  preferredHeight: number | null = null,
): string | null {
  const videos = formats.filter((format) => format.height !== null);

  if (videos.length === 0) {
    return null;
  }

  if (preferredHeight !== null) {
    const atOrBelow = videos
      .filter((format) => (format.height ?? 0) <= preferredHeight)
      .sort((a, b) => (b.height ?? 0) - (a.height ?? 0))[0];
    if (atOrBelow) {
      return atOrBelow.format_id;
    }
  }

  return (
    videos.find((format) => format.height === 1080) ??
    videos.find((format) => format.height === 720) ??
    videos[0]
  ).format_id;
}
