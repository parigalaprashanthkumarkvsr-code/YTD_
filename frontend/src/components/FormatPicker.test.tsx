import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import type { AudioFormat, DownloadKind, VideoFormat } from "../types";
import { FormatPicker } from "./FormatPicker";

const formats: VideoFormat[] = [
  {
    format_id: "137+140",
    label: "1080p MP4",
    ext: "mp4",
    height: 1080,
    filesize: 52_428_800,
  },
  {
    format_id: "136+140",
    label: "720p MP4",
    ext: "mp4",
    height: 720,
    filesize: 26_214_400,
  },
  {
    format_id: "bestaudio",
    label: "Audio only",
    ext: "m4a",
    height: null,
    filesize: 3_400_000,
  },
];

function Harness() {
  const [kind, setKind] = useState<DownloadKind>("video");
  const [selectedFormatId, setSelectedFormatId] = useState<string | null>("137+140");
  const [audioFormat, setAudioFormat] = useState<AudioFormat>("mp3");

  return (
    <FormatPicker
      formats={formats}
      kind={kind}
      onKindChange={setKind}
      selectedFormatId={selectedFormatId}
      onFormatChange={setSelectedFormatId}
      audioFormat={audioFormat}
      onAudioFormatChange={setAudioFormat}
    />
  );
}

describe("FormatPicker", () => {
  it("shows video qualities and marks the selected one", () => {
    render(<Harness />);

    expect(screen.getByRole("tab", { name: /video/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("radio", { name: /1080p MP4/i })).toBeChecked();
    expect(screen.getByRole("radio", { name: /720p MP4/i })).not.toBeChecked();
    expect(screen.getByText(/50.0 MB/)).toBeInTheDocument();
  });

  it("switches to audio and selects a codec", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("tab", { name: /audio/i }));

    expect(screen.queryByRole("radio", { name: /1080p MP4/i })).not.toBeInTheDocument();
    const m4a = screen.getByRole("radio", { name: /M4A/i });
    expect(m4a).not.toBeChecked();

    await user.click(m4a);
    expect(m4a).toBeChecked();
  });

  it("keeps the chosen video format when toggling tabs", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("radio", { name: /720p MP4/i }));
    await user.click(screen.getByRole("tab", { name: /audio/i }));
    await user.click(screen.getByRole("tab", { name: /video/i }));

    expect(screen.getByRole("radio", { name: /720p MP4/i })).toBeChecked();
  });
});
