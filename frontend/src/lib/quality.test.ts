import { describe, expect, it } from "vitest";

import type { VideoFormat } from "../types";
import { pickDefaultFormat } from "./quality";

function format(height: number, formatId = `${height}p`): VideoFormat {
  return {
    format_id: formatId,
    label: `${height}p MP4`,
    ext: "mp4",
    height,
    filesize: null,
  };
}

describe("pickDefaultFormat", () => {
  const formats = [format(2160), format(1080), format(720), format(480)];

  it("falls back to 1080p when there is no stored preference", () => {
    expect(pickDefaultFormat(formats)).toBe("1080p");
  });

  it("uses the stored quality when it is available", () => {
    expect(pickDefaultFormat(formats, 720)).toBe("720p");
  });

  it("uses the best available quality at or below the stored preference", () => {
    expect(pickDefaultFormat([format(1080), format(480)], 720)).toBe("480p");
  });

  it("falls back to the normal default when the preference is above every format", () => {
    expect(pickDefaultFormat([format(1080), format(720)], 2160)).toBe("1080p");
  });

  it("falls back to the normal default when the preference is below every format", () => {
    expect(pickDefaultFormat([format(2160), format(1080)], 480)).toBe("1080p");
  });

  it("returns null when there are no video formats", () => {
    expect(pickDefaultFormat([])).toBeNull();
  });
});
