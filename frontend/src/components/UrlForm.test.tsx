import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { UrlForm } from "./UrlForm";

describe("UrlForm", () => {
  it("rejects an empty submit", async () => {
    const user = userEvent.setup();
    render(<UrlForm onSubmit={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /fetch/i }));

    expect(screen.getByRole("alert")).toHaveTextContent("Paste a YouTube link first.");
  });

  it("rejects non-YouTube links", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<UrlForm onSubmit={onSubmit} />);

    await user.type(
      screen.getByLabelText("YouTube URL"),
      "https://example.com/watch?v=dQw4w9WgXcQ",
    );
    await user.click(screen.getByRole("button", { name: /fetch/i }));

    expect(screen.getByRole("alert")).toHaveTextContent("doesn't look like a YouTube");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("detects a valid link and submits it", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<UrlForm onSubmit={onSubmit} />);

    const input = screen.getByLabelText("YouTube URL");
    await user.type(input, "https://youtu.be/dQw4w9WgXcQ");

    expect(screen.getByText(/link detected/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /fetch/i }));

    expect(onSubmit).toHaveBeenCalledWith("https://youtu.be/dQw4w9WgXcQ");
  });

  it("accepts playlist links", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<UrlForm onSubmit={onSubmit} />);

    const input = screen.getByLabelText("YouTube URL");
    await user.type(input, "https://www.youtube.com/playlist?list=PL1234567890");

    expect(screen.getByText(/playlist/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /fetch/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      "https://www.youtube.com/playlist?list=PL1234567890",
    );
  });

  it("accepts bare youtube.com links", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<UrlForm onSubmit={onSubmit} />);

    await user.type(
      screen.getByLabelText("YouTube URL"),
      "youtube.com/watch?v=dQw4w9WgXcQ{Enter}",
    );

    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("does not submit while busy", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<UrlForm onSubmit={onSubmit} busy />);

    await user.type(
      screen.getByLabelText("YouTube URL"),
      "https://youtu.be/dQw4w9WgXcQ{Enter}",
    );

    expect(onSubmit).not.toHaveBeenCalled();
  });
});
