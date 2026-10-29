import { useCallback, useEffect, useState } from "react";

import type { AudioFormat, DownloadKind } from "../types";

const STORAGE_KEY = "ytd-history-v1";
const MAX_ENTRIES = 20;

export interface HistoryEntry {
  jobId: string;
  title: string;
  channel: string;
  kind: DownloadKind;
  label: string;
  audioFormat: AudioFormat | null;
  filename: string;
  completedAt: string;
}

function loadEntries(): HistoryEntry[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(
      (entry): entry is HistoryEntry =>
        typeof entry === "object" &&
        entry !== null &&
        typeof (entry as HistoryEntry).jobId === "string" &&
        typeof (entry as HistoryEntry).title === "string" &&
        typeof (entry as HistoryEntry).filename === "string" &&
        typeof (entry as HistoryEntry).completedAt === "string",
    );
  } catch {
    return [];
  }
}

export function useHistory() {
  const [entries, setEntries] = useState<HistoryEntry[]>(loadEntries);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
    } catch {
      // Storage can be unavailable; history then lasts for this tab only.
    }
  }, [entries]);

  const add = useCallback((entry: HistoryEntry) => {
    setEntries((current) => {
      if (current.some((item) => item.jobId === entry.jobId)) {
        return current;
      }
      return [entry, ...current].slice(0, MAX_ENTRIES);
    });
  }, []);

  const clear = useCallback(() => {
    setEntries([]);
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore unavailable storage.
    }
  }, []);

  return { entries, add, clear };
}
