import { cn } from "@/lib/utils";
import { VOICE_BG, VOICE_LABEL, VOICE_STATES, isVoiceState } from "./voice-taxonomy";

interface DistributionBarsProps {
  distribution: Record<string, number>;
}

export function DistributionBars({ distribution }: DistributionBarsProps) {
  const rows = VOICE_STATES.map((state) => ({ state, value: distribution[state] ?? 0 }))
    .filter((r) => r.value > 0)
    .sort((a, b) => b.value - a.value);

  const extra = Object.entries(distribution).filter(([k, v]) => !isVoiceState(k) && v > 0);

  return (
    <section className="card p-5">
      <h3 className="font-mono text-[11px] tracking-[0.16em] text-accent-link uppercase">Distribution</h3>
      <div className="mt-4 space-y-2.5">
        {rows.length === 0 && extra.length === 0 && (
          <p className="text-sm text-muted">No relationship distribution recorded.</p>
        )}
        {rows.map(({ state, value }) => (
          <div key={state} className="flex items-center gap-3">
            <span className="w-20 shrink-0 text-sm text-fg-secondary">{VOICE_LABEL[state]}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-pill bg-surface-input">
              <div className={cn("h-full rounded-pill", VOICE_BG[state])} style={{ width: `${value * 100}%` }} />
            </div>
            <span className="w-10 shrink-0 text-right font-mono text-xs text-muted tabular-nums">
              {value.toFixed(2)}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
