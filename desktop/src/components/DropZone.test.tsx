import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DropZone } from "@/components/DropZone";

function fileWithPath(name: string, path: string): File {
  const file = new File([""], name);
  Object.defineProperty(file, "path", { value: path });
  return file;
}

describe("DropZone", () => {
  it("emits the dropped file's absolute path", () => {
    const onPick = vi.fn();
    render(<DropZone onPick={onPick} />);
    fireEvent.drop(screen.getByText(/drop a song/i).closest("div")!, {
      dataTransfer: { files: [fileWithPath("the_weight.flac", "/music/the_weight.flac")] },
    });
    expect(onPick).toHaveBeenCalledWith("/music/the_weight.flac");
  });

  it("does not emit when disabled", () => {
    const onPick = vi.fn();
    render(<DropZone onPick={onPick} disabled />);
    fireEvent.drop(screen.getByText(/drop a song/i).closest("div")!, {
      dataTransfer: { files: [fileWithPath("x.flac", "/music/x.flac")] },
    });
    expect(onPick).not.toHaveBeenCalled();
  });

  it("falls back to a mock path when no native bridge is present", async () => {
    const onPick = vi.fn();
    render(<DropZone onPick={onPick} />);
    await userEvent.click(screen.getByRole("button", { name: /choose a file/i }));
    expect(onPick).toHaveBeenCalledTimes(1);
  });
});
