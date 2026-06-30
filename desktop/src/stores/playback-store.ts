import { createStore } from "zustand/vanilla";
import { useStore } from "zustand";

const clamp01 = (n: number) => Math.min(1, Math.max(0, n));

// The shared time spine: playhead + hover position as fractions of the track.
// Time-aligned tabs subscribe here to draw a guide at the same x.
interface PlaybackState {
  positionPct: number;
  hoverPct: number | null;
  seek: (pct: number) => void;
  hover: (pct: number | null) => void;
}

export const playbackStore = createStore<PlaybackState>((set) => ({
  positionPct: 0,
  hoverPct: null,
  seek: (pct) => set({ positionPct: clamp01(pct) }),
  hover: (pct) => set({ hoverPct: pct === null ? null : clamp01(pct) }),
}));

export function usePlayback<T>(selector: (state: PlaybackState) => T): T {
  return useStore(playbackStore, selector);
}
