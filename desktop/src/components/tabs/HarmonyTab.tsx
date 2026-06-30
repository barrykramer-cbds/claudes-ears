import { TimeField } from "@/components/workspace/TimeField";
import { Eyebrow } from "@/components/ui/eyebrow";
import { StatGrid, type Stat } from "./StatGrid";
import { TabEmpty } from "./TabEmpty";
import { cn } from "@/lib/utils";
import type { PerceptionDocument } from "@/lib/schemas";

interface HarmonyTabProps {
  doc: PerceptionDocument;
}

const FN_BG: Record<string, string> = {
  tonic: "bg-data-green/70",
  dominant: "bg-data-orange/70",
  subdominant: "bg-data-blue/70",
  predominant: "bg-data-blue/70",
};

interface Block {
  start: number;
  end: number;
  chord: string;
  numeral: string | null;
  fn: string | null;
}

export function HarmonyTab({ doc }: HarmonyTabProps) {
  const harmony = doc.harmony;
  const duration = doc.track.duration_s ?? harmony?.chords?.tempo ?? 0;
  const analyzed = harmony?.theory?.analyzed_chords ?? [];
  const segments = harmony?.chords?.segments ?? [];

  const blocks: Block[] = analyzed.length
    ? analyzed.map((c) => ({
        start: c.start,
        end: c.end,
        chord: c.chord,
        numeral: c.analysis?.numeral ?? c.label,
        fn: c.analysis?.function ?? null,
      }))
    : segments.map((s) => ({ start: s.start, end: s.end, chord: s.chord, numeral: null, fn: null }));

  if (!harmony || (blocks.length === 0 && !harmony.theory)) {
    return <TabEmpty>No harmonic analysis for this track.</TabEmpty>;
  }

  const theory = harmony.theory;
  const rhythm = harmony.harmonic_rhythm;
  const progression = harmony.chords?.chord_sequence_summary ?? [];

  const stats: Stat[] = [
    { label: "key", value: theory ? `${theory.key} ${theory.mode}` : "—" },
    { label: "confidence", value: theory?.key_confidence?.toFixed(2) ?? "—" },
    { label: "chords/bar", value: rhythm?.avg_changes_per_bar?.toFixed(1) ?? "—" },
    { label: "cadences", value: theory ? String(theory.total_cadences) : "—" },
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6 motion-safe:animate-[step-in_240ms_ease-out]">
      <section className="card px-6 pt-5 pb-4">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-semibold text-fg">Chords across time</h2>
          {rhythm?.harmonic_arc && <span className="text-xs text-muted">{rhythm.harmonic_arc}</span>}
        </div>

        <TimeField className="mt-4">
          <div className="relative h-14 overflow-hidden rounded-button bg-surface-input">
            {blocks.map((b, i) => (
              <div
                key={i}
                className={cn(
                  "absolute inset-y-0 flex flex-col items-center justify-center gap-0.5 border-r border-bg/40",
                  FN_BG[b.fn ?? ""] ?? "bg-surface-hover",
                )}
                style={{
                  left: `${(b.start / duration) * 100}%`,
                  width: `${Math.max(((b.end - b.start) / duration) * 100, 1.5)}%`,
                  minWidth: "8px",
                }}
              >
                <span className="font-mono text-xs font-medium text-fg">{b.chord}</span>
                {b.numeral && <span className="font-mono text-[10px] text-fg/60">{b.numeral}</span>}
              </div>
            ))}
          </div>
        </TimeField>

        {progression.length > 0 && (
          <p className="mt-3 font-mono text-sm text-muted">
            {progression.map((c, i) => (
              <span key={i}>
                {i > 0 && <span className="text-faint"> → </span>}
                <span className="text-fg-secondary">{c}</span>
              </span>
            ))}
          </p>
        )}
      </section>

      <div className="grid gap-4 md:grid-cols-[1fr_1.15fr]">
        <section className="card p-5">
          <Eyebrow>Key · vocabulary</Eyebrow>
          <StatGrid stats={stats} className="mt-4 grid-cols-2" />
          {theory && theory.unique_numerals.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {theory.unique_numerals.map((n) => (
                <span
                  key={n}
                  className="rounded-button bg-surface-raised px-2 py-1 font-mono text-xs text-fg-secondary"
                >
                  {n}
                </span>
              ))}
            </div>
          )}
        </section>

        <section className="card p-5">
          <Eyebrow>Cadences</Eyebrow>
          <ul className="mt-4 space-y-3">
            {theory?.cadences.length ? (
              theory.cadences.map((c, i) => (
                <li key={i} className="border-b border-border pb-3 last:border-0 last:pb-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-fg">
                      {c.from} <span className="text-faint">→</span> {c.to}
                    </span>
                    <span className="text-xs text-muted">
                      {c.type} · {c.strength}
                    </span>
                  </div>
                  <p className="mt-1 font-serif text-sm text-fg-secondary italic">{c.narrative}</p>
                </li>
              ))
            ) : (
              <li className="text-sm text-muted">No cadences resolved.</li>
            )}
          </ul>
        </section>
      </div>
    </div>
  );
}
