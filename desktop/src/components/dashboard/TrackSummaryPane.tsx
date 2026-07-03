import { Eyebrow } from "@/components/ui/eyebrow";
import type { LibraryEntry } from "@/lib/library-entries";
import { formatClock } from "@/lib/utils";

// Shown for a track that exists only in the DuckDB index — the sidecar has no
// per-track perception endpoint yet (build-plan 4.4.2), so the full lenses can't open.
export function TrackSummaryPane({ entry }: { entry: LibraryEntry }) {
  const stats: [string, string | null][] = [
    ["key", entry.keyMode],
    ["tempo", entry.tempo != null ? `${Math.round(entry.tempo)} bpm` : null],
    ["length", entry.durationS != null ? formatClock(entry.durationS) : null],
    ["reads", entry.verdict],
  ];

  return (
    <div className="grid min-h-0 flex-1 place-items-center overflow-auto p-6">
      <div className="card w-full max-w-md space-y-4 p-6">
        <div className="space-y-1">
          <Eyebrow>From the library</Eyebrow>
          <h1 className="text-lg font-semibold tracking-[-0.02em] text-fg">{entry.title}</h1>
          {entry.artist && <p className="text-sm text-muted">{entry.artist}</p>}
        </div>

        <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-button border border-border bg-border">
          {stats
            .filter(([, v]) => v !== null)
            .map(([k, v]) => (
              <div key={k} className="bg-surface-raised px-3 py-2">
                <dt className="font-mono text-[10px] tracking-[0.14em] text-faint uppercase">{k}</dt>
                <dd className="font-mono text-sm text-fg">{v}</dd>
              </div>
            ))}
        </dl>

        <p className="text-xs text-muted">
          The full listening view opens for tracks analyzed in this session. Re-analyze the source
          file to reopen every lens.
        </p>
      </div>
    </div>
  );
}
