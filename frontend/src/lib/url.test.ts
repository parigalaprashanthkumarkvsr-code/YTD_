import { describe, expect, it } from "vitest";

import {
  extractYouTubeId,
  extractYouTubePlaylistId,
  isYouTubeUrl,
  parseYouTubeUrl,
} from "./url";

describe("YouTube URL validation", () => {
  it.each([
    ["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["https://youtu.be/dQw4w9WgXcQ?t=10", "dQw4w9WgXcQ"],
    ["https://m.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"],
  ])("accepts %s", (url, id) => {
    expect(isYouTubeUrl(url)).toBe(true);
    expect(extractYouTubeId(url)).toBe(id);
  });

  it.each([
    ["https://example.com/watch?v=dQw4w9WgXcQ"],
    ["https://youtube.com.evil.test/watch?v=dQw4w9WgXcQ"],
    ["https://music.youtube.com/watch?v=dQw4w9WgXcQ"],
    ["https://www.youtube.com:8443/watch?v=dQw4w9WgXcQ"],
    ["https://www.youtube.com/playlist?list=PL123"],
    ["https://www.youtube.com/watch?v=short"],
    [""],
  ])("rejects %s", (url) => {
    expect(isYouTubeUrl(url)).toBe(false);
    expect(extractYouTubeId(url)).toBeNull();
  });

  it.each([
    "https://www.youtube.com/playlist?list=PL1234567890",
    "https://m.youtube.com/playlist?list=PL1234567890&si=share",
    "youtube.com/playlist?list=PL1234567890",
  ])("detects playlist %s", (url) => {
    expect(isYouTubeUrl(url)).toBe(true);
    expect(extractYouTubePlaylistId(url)).toBe("PL1234567890");
    expect(parseYouTubeUrl(url)).toEqual({
      kind: "playlist",
      id: "PL1234567890",
    });
    expect(extractYouTubeId(url)).toBeNull();
  });
});
