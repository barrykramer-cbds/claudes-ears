import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AddTrackModal } from "@/components/AddTrackModal";

describe("AddTrackModal", () => {
  const onClose = vi.fn();
  const onSubmit = vi.fn();

  beforeEach(() => {
    onClose.mockClear();
    onSubmit.mockClear();
  });

  it("submits a YouTube URL as source_url", async () => {
    render(<AddTrackModal open onClose={onClose} onSubmit={onSubmit} />);
    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Video URL"),
      "https://www.youtube.com/watch?v=abc123",
    );
    await user.click(screen.getByRole("button", { name: "Analyze" }));
    expect(onSubmit).toHaveBeenCalledWith({
      source_url: "https://www.youtube.com/watch?v=abc123",
    });
  });

  it("rejects a non-URL and explains the fix", async () => {
    render(<AddTrackModal open onClose={onClose} onSubmit={onSubmit} />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Video URL"), "not a url");
    await user.click(screen.getByRole("button", { name: "Analyze" }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText(/Paste a full http\(s\) link/)).toBeInTheDocument();
  });

  it("submits a local path as audio_path when no picker bridge exists", async () => {
    render(<AddTrackModal open onClose={onClose} onSubmit={onSubmit} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "From a file" }));
    await user.type(screen.getByLabelText("Local file path"), "/music/song.flac");
    await user.click(screen.getByRole("button", { name: "Analyze" }));
    expect(onSubmit).toHaveBeenCalledWith({ audio_path: "/music/song.flac" });
  });

  it("closes without submitting on Cancel", async () => {
    render(<AddTrackModal open onClose={onClose} onSubmit={onSubmit} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalled();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
