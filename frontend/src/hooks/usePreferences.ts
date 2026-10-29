import { useCallback, useEffect, useState } from "react";

import type { PlaylistQuality } from "../types";

const STORAGE_KEY = "ytd-preferences-v1";
const DEFAULT_PLAYLIST_QUALITY: PlaylistQuality | null = 1080;
const DEFAULT_PREFERRED_HEIGHT: number | null = null;

const PLAYLIST_QUALITIES: readonly (PlaylistQuality | null)[] = [
  null,
  2160,
  1440,
  1080,
  720,
  480,
  360,
];

interface Preferences {
  playlistQuality: PlaylistQuality | null;
  preferredHeight: number | null;
}

function isPlaylistQuality(value: unknown): value is PlaylistQuality | null {
  return PLAYLIST_QUALITIES.includes(value as PlaylistQuality | null);
}

function isPreferredHeight(value: unknown): value is number | null {
  return (
    value === null ||
    (typeof value === "number" &&
      Number.isFinite(value) &&
      Number.isInteger(value) &&
      value > 0 &&
      value <= 4320)
  );
}

function loadPreferences(): Preferences {
  const defaults: Preferences = {
    playlistQuality: DEFAULT_PLAYLIST_QUALITY,
    preferredHeight: DEFAULT_PREFERRED_HEIGHT,
  };

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return defaults;
    }
    const parsed = JSON.parse(raw) as unknown;
    if (typeof parsed !== "object" || parsed === null) {
      return defaults;
    }
    const stored = parsed as Record<string, unknown>;
    return {
      playlistQuality: isPlaylistQuality(stored.playlistQuality)
        ? stored.playlistQuality
        : defaults.playlistQuality,
      preferredHeight: isPreferredHeight(stored.preferredHeight)
        ? stored.preferredHeight
        : defaults.preferredHeight,
    };
  } catch {
    return defaults;
  }
}

export function usePreferences() {
  const [preferences, setPreferences] = useState<Preferences>(loadPreferences);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
    } catch {
      // Storage can be unavailable; the current tab still keeps the choice.
    }
  }, [preferences]);

  const setPlaylistQuality = useCallback((quality: PlaylistQuality | null) => {
    setPreferences((current) =>
      current.playlistQuality === quality
        ? current
        : { ...current, playlistQuality: quality },
    );
  }, []);

  const setPreferredHeight = useCallback((height: number | null) => {
    setPreferences((current) =>
      current.preferredHeight === height
        ? current
        : { ...current, preferredHeight: height },
    );
  }, []);

  return { ...preferences, setPlaylistQuality, setPreferredHeight };
}

export { STORAGE_KEY as PREFERENCES_STORAGE_KEY };
