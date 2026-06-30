import { TimeField } from "@/components/workspace/TimeField";
import { TabEmpty } from "./TabEmpty";
import { cn, formatClock, parseClock } from "@/lib/utils";
import type { PerceptionDocument } from "@/lib/schemas";

interface StructureTabProps {
  doc: PerceptionDocument;
}

const STATE_HUE: Record<string, string> = {
  weary: "bg-data-slate/40",
  hopeful: "bg-data-green/40",
  lifted: "bg-data-yellow/40",
  joyful: "bg-data-orange/40",
  tense: "bg-data-red/40",
  calm: "bg-data-blue/40",
};

const THIRD_X = [1 / 6, 1 / 2, 5 / 6];

function polyline(values: (number | null)[]): string {
  return values
    .map((v, i) => (v === null ? null : `${THIRD_X[i]! * 100},${(1 - v) * 100}`))
    .filter((p): p is string => p !== null)
    .join(" ");
}

export function StructureTab({ doc }: StructureTabProps) {
  const duration = doc.track.duration_s ?? 0;
  const emotion = doc.emotion;
  const arc = doc.structure?.narrative;

  if (!emotion && !arc) return <TabEmpty>No structural reading for this track.</TabEmpty>;

  const energy = arc?.arc?.e_thirds ?? [];
  const tension = arc?.arc?.t_thirds ?? [];
  const markers = [
    arc?.climax && { label: "climax", time: arc.climax.time },
    arc?.peak_tension && { label: "peak tension", time: arc.peak_tension.time },
    arc?.quietest && { label: "quietest", time: arc.quietest.time },
  ].filter((m): m is { label: string; time: string } => Boolean(m));

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6 motion-safe:animate-[step-in_240ms_ease-out]">
      <section className="card px-6 pt-5 pb-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-semibold text-fg">Energy &amp; tension across the song</h2>
          <div className="flex gap-4 font-mono text-[10px] text-muted">
            <span className="flex items-center gap-1.5">
              <span className="h-0.5 w-3 bg-data-yellow" /> energy
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-0.5 w-3 bg-data-red" /> tension
            </span>
          </div>
        </div>

        <TimeField className="mt-4">
          <div className="relative h-44">
            {[25, 50, 75].map((top) => (
              <div key={top} className="absolute inset-x-0 h-px bg-edge" style={{ top: `${top}%` }} />
            ))}
            <svg
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              className="h-full w-full overflow-visible"
              aria-hidden
            >
              {energy.length > 0 && (
                <polyline
                  className="curve-line"
                  points={polyline(energy)}
                  pathLength={1}
                  fill="none"
                  stroke="var(--color-data-yellow)"
                  strokeWidth={1.5}
                  strokeLinejoin="round"
                  vectorEffect="non-scaling-stroke"
                />
              )}
              {tension.length > 0 && (
                <polyline
                  className="curve-line"
                  points={polyline(tension)}
                  pathLength={1}
                  fill="none"
                  stroke="var(--color-data-red)"
                  strokeWidth={1.5}
                  strokeLinejoin="round"
                  vectorEffect="non-scaling-stroke"
                />
              )}
            </svg>
            {markers.map((m) => {
              const secs = parseClock(m.time);
              if (secs === null || duration === 0) return null;
              return (
                <div
                  key={m.label}
                  className="absolute inset-y-0 w-px bg-border-strong"
                  style={{ left: `${(secs / duration) * 100}%` }}
                >
                  <span className="absolute top-1 left-1 font-mono text-[10px] whitespace-nowrap text-faint">
                    {m.label}
                  </span>
                </div>
              );
            })}
          </div>

          {emotion && emotion.phases.length > 0 && (
            <div className="relative mt-2 flex h-7 overflow-hidden rounded-button">
              {emotion.phases.map((p, i) => {
                const start = parseClock(p.start) ?? 0;
                const end = parseClock(p.end) ?? duration;
                const width = duration ? ((end - start) / duration) * 100 : 0;
                return (
                  <div
                    key={i}
                    className={cn(
                      "flex items-center justify-center border-r border-bg/40 last:border-0",
                      STATE_HUE[p.state] ?? "bg-surface-hover",
                    )}
                    style={{ width: `${width}%` }}
                    title={`${p.state} · ${formatClock(start)}–${formatClock(end)}`}
                  >
                    <span className="truncate px-1 text-[11px] text-fg-secondary">{p.state}</span>
                  </div>
                );
              })}
            </div>
          )}
        </TimeField>
      </section>

      {emotion?.narrative && (
        <p className="max-w-2xl font-serif text-[15px] leading-relaxed text-fg-secondary italic">
          “{emotion.narrative}”
        </p>
      )}
    </div>
  );
}
