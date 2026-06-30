import { beforeEach, describe, expect, it } from "vitest";
import { libraryStore } from "./library-store";
import { mockPerception } from "@/mock/perception";
import type { PerceptionDocument } from "@/lib/schemas";

const second: PerceptionDocument = {
  ...mockPerception,
  track: { ...mockPerception.track, id: "tokyo_live", title: "Tokyo, Live" },
};

describe("library-store", () => {
  beforeEach(() => libraryStore.getState().clear());

  it("adds tracks newest-first", () => {
    libraryStore.getState().add(mockPerception);
    libraryStore.getState().add(second);
    expect(libraryStore.getState().tracks.map((t) => t.track.id)).toEqual([
      "tokyo_live",
      "the_weight_studio",
    ]);
  });

  it("dedupes by track id, moving the re-added track to the front", () => {
    libraryStore.getState().add(mockPerception);
    libraryStore.getState().add(second);
    libraryStore.getState().add(mockPerception);
    expect(libraryStore.getState().tracks.map((t) => t.track.id)).toEqual([
      "the_weight_studio",
      "tokyo_live",
    ]);
  });

  it("looks a track up by id", () => {
    libraryStore.getState().add(mockPerception);
    expect(libraryStore.getState().get("the_weight_studio")?.track.title).toBe("The Weight");
    expect(libraryStore.getState().get("missing")).toBeUndefined();
  });
});
