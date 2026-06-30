import { formatClock } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { VOICE_BG, VOICE_LABEL, VOICE_STATES, type VoiceState } from "./voice-taxonomy";

interface BeeswarmProps {
  distribution: Record<string, number>;
  durationS: number;
}

const TOTAL_DOTS = 90;

// Deterministic PRNG so dot positions are stable across renders (React Compiler-safe).
function mulberry32(seed: number): () => number {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function gauss(rng: () => number): number {
  let x = 0;
  for (let i = 0; i < 4; i++) x += rng();
  return (x / 4 - 0.5) * 2;
}

const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, n));

interface Dot {
  state: VoiceState;
  x: number;
  y: number;
  o: number;
}

interface Cluster {
  state: VoiceState;
  cx: number;
  meanY: number;
  dots: Dot[];
}

function layout(distribution: Record<string, number>): Cluster[] {
  return VOICE_STATES.map((state, col) => {
    const cx = (col + 0.5) / VOICE_STATES.length;
    const n = Math.round((distribution[state] ?? 0) * TOTAL_DOTS);
    const rng = mulberry32((col + 1) * 9973);
    const meanY = 0.3 + rng() * 0.34;
    const dots = Array.from({ length: n }, (): Dot => ({
      state,
      x: clamp(cx + gauss(rng) * 0.045, 0.02, 0.98),
      y: clamp(meanY + gauss(rng) * 0.3, 0.05, 0.95),
      o: 0.5 + rng() * 0.5,
    }));
    return { state, cx, meanY, dots };
  });
}

export function Beeswarm({ distribution, durationS }: BeeswarmProps) {
  const clusters = layout(distribution);
  const hasDots = clusters.some((c) => c.dots.length > 0);
  let dotIndex = 0;

  return (
    <section className="card px-6 pt-5 pb-4">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-fg">Vocal relationship · density over time</h2>
        <span className="font-mono text-xs text-faint">{formatClock(durationS)}</span>
      </div>

      <div className="relative mt-4 h-[260px] border-b border-border">
        {!hasDots && (
          <p className="absolute inset-0 grid place-items-center text-sm text-muted">
            No relationship moments surfaced for this track.
          </p>
        )}
        {[20, 40, 60, 80].map((top) => (
          <div key={top} className="absolute inset-x-0 h-px bg-edge" style={{ top: `${top}%` }} />
        ))}
        {clusters.map((c) =>
          c.dots.length === 0 ? null : (
            <div
              key={`step-${c.state}`}
              className={cn("absolute h-0.5 -translate-x-1/2 rounded-pill opacity-50", VOICE_BG[c.state])}
              style={{ left: `${c.cx * 100}%`, top: `${c.meanY * 100}%`, width: `${100 / VOICE_STATES.length}%` }}
              aria-hidden
            />
          ),
        )}
        {clusters.flatMap((c) =>
          c.dots.map((d, i) => {
            const delay = Math.min(dotIndex++ * 5, 380);
            return (
              <span
                key={`${c.state}-${i}`}
                className={cn("swarm-dot absolute size-[7px] rounded-full shadow-[0_0_7px_-1px_currentColor]", VOICE_BG[d.state])}
                style={
                  {
                    left: `${d.x * 100}%`,
                    top: `${d.y * 100}%`,
                    "--o": d.o,
                    "--d": `${delay}ms`,
                  } as React.CSSProperties
                }
                aria-hidden
              />
            );
          }),
        )}
      </div>

      <div className="mt-3 flex">
        {VOICE_STATES.map((state) => (
          <span key={state} className="flex-1 text-center font-mono text-[10px] text-muted">
            {VOICE_LABEL[state]}
          </span>
        ))}
      </div>
    </section>
  );
}
