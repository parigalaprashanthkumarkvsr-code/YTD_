import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { JobState } from "../types";
import { ProgressBar } from "./ProgressBar";

function job(overrides: Partial<JobState> = {}): JobState {
  return {
    id: "abc123",
    status: "downloading",
    percent: 42.5,
    speed: "3.2MiB/s",
    eta: 18,
    filename: null,
    error: null,
    created_at: "2026-10-29T09:00:00Z",
    playlist: null,
    ...overrides,
  };
}

describe("ProgressBar", () => {
  it("renders percent, speed, eta and exposes progress semantics", () => {
    render(<ProgressBar job={job()} onCancel={vi.fn()} />);

    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "42.5");
    expect(screen.getByText(/3.2MiB\/s/)).toBeInTheDocument();
    expect(screen.getByText(/18s left/)).toBeInTheDocument();
    expect(screen.getByText("downloading")).toBeInTheDocument();
  });

  it("cancels a running job", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<ProgressBar job={job()} onCancel={onCancel} />);

    await user.click(screen.getByRole("button", { name: /cancel/i }));

    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("shows the current playlist item", () => {
    render(
      <ProgressBar
        job={job({
          percent: 25,
          playlist: {
            total_items: 4,
            completed_items: 1,
            current_item: 2,
            current_title: "Second video",
            skipped_items: 1,
          },
        })}
        onCancel={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/video 2 of 4 · Second video · 1 skipped/i),
    ).toBeInTheDocument();
  });

  it("shows a queued state", () => {
    render(
      <ProgressBar
        job={job({ status: "queued", percent: 0, speed: null, eta: null })}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByText(/waiting for a slot/i)).toBeInTheDocument();
  });
});
