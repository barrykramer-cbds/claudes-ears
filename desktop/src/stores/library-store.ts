import { createStore } from "zustand/vanilla";
import { useStore } from "zustand";
import type { PerceptionDocument } from "@/lib/schemas";

// The analyzed-track cache, newest-first, deduped by track id.
// Phase 4 swaps the seeding from job-completion to a GET /library hydrate.
interface LibraryState {
  tracks: PerceptionDocument[];
  add: (doc: PerceptionDocument) => void;
  get: (id: string) => PerceptionDocument | undefined;
  clear: () => void;
}

export const libraryStore = createStore<LibraryState>((set, get) => ({
  tracks: [],
  add: (doc) =>
    set((s) => ({ tracks: [doc, ...s.tracks.filter((t) => t.track.id !== doc.track.id)] })),
  get: (id) => get().tracks.find((t) => t.track.id === id),
  clear: () => set({ tracks: [] }),
}));

export function useLibrary<T>(selector: (state: LibraryState) => T): T {
  return useStore(libraryStore, selector);
}
