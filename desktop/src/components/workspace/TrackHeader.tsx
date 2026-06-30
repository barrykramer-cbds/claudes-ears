import { formatClock } from "@/lib/utils";
import type { PerceptionDocument } from "@/lib/schemas";

export function TrackHeader({ doc }: { doc: PerceptionDocument }) {
  const { track, harmony, rhythm } = doc;
  const key = harmony?.theory ? `${harmony.theory.key} ${harmony.theory.mode}` : null;
  const bpm = rhythm?.groove ? `${Math.round(rhythm.groove.tempo)} bpm` : null;
  const duration = track.duration_s ? formatClock(track.duration_s) : null;
  const meta = [key, bpm, duration].filter(Boolean).join(" · ");

  return (
    <header className="flex shrink-0 items-baseline justify-between gap-4 px-6 pt-5 pb-3">
      <h1 className="min-w-0 truncate text-[17px] font-semibold tracking-[-0.02em] text-fg">
        {track.title ?? track.id}
        {track.artist && <span className="font-normal text-faint"> · {track.artist}</span>}
      </h1>
      {meta && <span className="shrink-0 font-mono text-xs text-muted">{meta}</span>}
    </header>
  );
}
