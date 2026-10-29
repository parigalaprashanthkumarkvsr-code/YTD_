import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { PlaylistItem } from "../types";
import { PlaylistItemList } from "./PlaylistItemList";

const ITEMS: PlaylistItem[] = [
  {
    id: "video-1",
    title: "First video",
    duration: 100,
    thumbnail: "https://img.example/one.jpg",
  },
  {
    id: "video-2",
    title: "Second video",
    duration: 200,
    thumbnail: null,
  },
  {
    id: "video-3",
    title: "Third video",
    duration: 300,
    thumbnail: "https://img.example/three.jpg",
  },
];

describe("PlaylistItemList", () => {
  it("renders every video and reports checked items", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    const onSelectAll = vi.fn();
    const onClear = vi.fn();

    render(
      <PlaylistItemList
        items={ITEMS}
        selectedIds={["video-1", "video-2"]}
        onToggle={onToggle}
        onSelectAll={onSelectAll}
        onClear={onClear}
      />,
    );

    expect(screen.getByText("2 of 3 selected")).toBeInTheDocument();
    expect(screen.getByText("First video")).toBeInTheDocument();
    expect(screen.getByText("video 1 · 1:40")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /first video/i })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /third video/i })).not.toBeChecked();

    await user.click(screen.getByRole("checkbox", { name: /third video/i }));
    expect(onToggle).toHaveBeenCalledWith("video-3");

    await user.click(screen.getByRole("button", { name: /select all/i }));
    expect(onSelectAll).toHaveBeenCalledOnce();

    await user.click(screen.getByRole("button", { name: /clear/i }));
    expect(onClear).toHaveBeenCalledOnce();
  });

  it("disables select all when every video is checked", () => {
    render(
      <PlaylistItemList
        items={ITEMS}
        selectedIds={ITEMS.map((item) => item.id)}
        onToggle={vi.fn()}
        onSelectAll={vi.fn()}
        onClear={vi.fn()}
      />,
    );

    expect(screen.getByText("3 of 3 selected")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /select all/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /clear/i })).toBeEnabled();
  });

  it("disables clear when nothing is checked", () => {
    render(
      <PlaylistItemList
        items={ITEMS}
        selectedIds={[]}
        onToggle={vi.fn()}
        onSelectAll={vi.fn()}
        onClear={vi.fn()}
      />,
    );

    expect(screen.getByText("0 of 3 selected")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /select all/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /clear/i })).toBeDisabled();
  });
});
