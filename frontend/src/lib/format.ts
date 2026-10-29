import type { JobStatus } from "../types";

export function formatDuration(totalSeconds: number | null | undefined): string {
  if (!totalSeconds || totalSeconds <= 0) {
    return "--:--";
  }
  const seconds = Math.round(totalSeconds);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = seconds % 60;
  const pad = (value: number) => value.toString().padStart(2, "0");
  return hours > 0
    ? `${hours}:${pad(minutes)}:${pad(remainder)}`
    : `${minutes}:${pad(remainder)}`;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes || bytes <= 0) {
    return "size unknown";
  }
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  const digits = value >= 100 || index === 0 ? 0 : 1;
  return `${value.toFixed(digits)} ${units[index]}`;
}

export function formatEta(seconds: number | null | undefined): string | null {
  if (seconds === null || seconds === undefined || seconds < 0) {
    return null;
  }
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds % 60);
  return `${minutes}m ${remainder.toString().padStart(2, "0")}s`;
}

export function formatHistoryDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "unknown time";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function statusLabel(status: JobStatus): string {
  switch (status) {
    case "queued":
      return "queued";
    case "downloading":
      return "downloading";
    case "processing":
      return "processing";
    case "done":
      return "done";
    case "error":
      return "error";
    case "cancelled":
      return "cancelled";
  }
}
