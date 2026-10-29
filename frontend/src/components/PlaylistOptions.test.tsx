import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PlaylistOptions } from "./PlaylistOptions";

describe("PlaylistOptions", () => {
  it("selects a playlist quality cap", async () => {
    const user = userEvent.setup();
    const onQualityChange = vi.fn();
    render(
      <PlaylistOptions
        kind="video"
        onKindChange={vi.fn()}
        quality={null}
        onQualityChange={onQualityChange}
        audioFormat="mp3"
        onAudioFormatChange={vi.fn()}
        videoCount={12}
      />,
    );

    expect(screen.getByText(/12 videos/i)).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /720p or lower/i }));

    expect(onQualityChange).toHaveBeenCalledWith(720);
  });

  it("switches to audio and picks a format", async () => {
    const user = userEvent.setup();
    const onKindChange = vi.fn();
    const onAudioFormatChange = vi.fn();
    render(
      <PlaylistOptions
        kind="video"
        onKindChange={onKindChange}
        quality={1080}
        onQualityChange={vi.fn()}
        audioFormat="mp3"
        onAudioFormatChange={onAudioFormatChange}
        videoCount={3}
      />,
    );

    await user.click(screen.getByRole("tab", { name: /audio/i }));
    expect(onKindChange).toHaveBeenCalledWith("audio");
  });

  it("renders audio formats when the audio tab is active", async () => {
    const user = userEvent.setup();
    const onAudioFormatChange = vi.fn();
    render(
      <PlaylistOptions
        kind="audio"
        onKindChange={vi.fn()}
        quality={1080}
        onQualityChange={vi.fn()}
        audioFormat="mp3"
        onAudioFormatChange={onAudioFormatChange}
        videoCount={3}
      />,
    );

    await user.click(screen.getByRole("radio", { name: /M4A/i }));
    expect(onAudioFormatChange).toHaveBeenCalledWith("m4a");
  });
});
