import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { PREFERENCES_STORAGE_KEY, usePreferences } from "./usePreferences";

describe("usePreferences", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("starts with 1080p for playlists and no single-video preference", () => {
    const { result } = renderHook(() => usePreferences());

    expect(result.current.playlistQuality).toBe(1080);
    expect(result.current.preferredHeight).toBeNull();
  });

  it("stores the chosen playlist quality", () => {
    const { result } = renderHook(() => usePreferences());

    act(() => result.current.setPlaylistQuality(720));

    expect(result.current.playlistQuality).toBe(720);
    expect(JSON.parse(window.localStorage.getItem(PREFERENCES_STORAGE_KEY) ?? "{}")).toEqual({
      playlistQuality: 720,
      preferredHeight: null,
    });
  });

  it("stores the chosen single-video height", () => {
    const { result } = renderHook(() => usePreferences());

    act(() => result.current.setPreferredHeight(480));

    expect(result.current.preferredHeight).toBe(480);
    expect(JSON.parse(window.localStorage.getItem(PREFERENCES_STORAGE_KEY) ?? "{}")).toEqual({
      playlistQuality: 1080,
      preferredHeight: 480,
    });
  });

  it("restores saved preferences", () => {
    window.localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ playlistQuality: null, preferredHeight: 1440 }),
    );

    const { result } = renderHook(() => usePreferences());

    expect(result.current.playlistQuality).toBeNull();
    expect(result.current.preferredHeight).toBe(1440);
  });

  it("ignores invalid stored values", () => {
    window.localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ playlistQuality: 999, preferredHeight: "large" }),
    );

    const { result } = renderHook(() => usePreferences());

    expect(result.current.playlistQuality).toBe(1080);
    expect(result.current.preferredHeight).toBeNull();
  });

  it("ignores malformed storage", () => {
    window.localStorage.setItem(PREFERENCES_STORAGE_KEY, "{not json");

    const { result } = renderHook(() => usePreferences());

    expect(result.current.playlistQuality).toBe(1080);
    expect(result.current.preferredHeight).toBeNull();
  });
});
