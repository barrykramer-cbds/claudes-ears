import { Eyebrow } from "@/components/ui/eyebrow";
import { StatGrid, type Stat } from "./StatGrid";
import { TabEmpty } from "./TabEmpty";
import { cn } from "@/lib/utils";
import type { PerceptionDocument } from "@/lib/schemas";

interface SpaceTabProps {
  doc: PerceptionDocument;
}

const DISTANCE_Y: Record<string, number> = {
  "near-field": 0.78,
  close: 0.7,
  intimate: 0.74,
  mid: 0.5,
  medium: 0.5,
  far: 0.28,
  distant: 0.18,
};

const clamp01 = (n: number) => Math.min(1, Math.max(0, n));

export function SpaceTab({ doc }: SpaceTabProps) {
  const stereo = doc.spatial?.stereo;
  const depth = doc.spatial?.depth;

  if (!stereo && !depth) return <TabEmpty>No spatial reading for this track.</TabEmpty>;

  const balance = stereo?.lr_balance ?? 0;
  const width = stereo?.stereo_width ?? 0;
  const distanceY = depth ? (DISTANCE_Y[depth.perceived_distance] ?? 0.5) : 0.5;
  const bands = stereo?.band_width ?? {};
  const bandRows = (["low", "mid", "high"] as const).map((b) => ({ band: b, value: bands[b] ?? 0 }));

  const roomStats: Stat[] = [
    { label: "room", value: depth?.room_size ?? "—" },
    { label: "distance", value: depth?.perceived_distance ?? "—" },
    { label: "rt60", value: depth?.rt60_estimate?.toFixed(2) ?? "—", unit: depth ? "s" : undefined },
    { label: "wetness", value: depth?.wetness_index?.toFixed(2) ?? "—" },
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6 motion-safe:animate-[step-in_240ms_ease-out]">
      <div className="grid gap-4 md:grid-cols-[1.3fr_1fr]">
        <section className="card px-6 pt-5 pb-5">
          <div className="flex items-baseline justify-between">
            <h2 className="text-sm font-semibold text-fg">Stereo field</h2>
            <span className="text-xs text-muted">{depth?.spatial_placement}</span>
          </div>

          <div className="relative mt-4 h-56 overflow-hidden rounded-button bg-surface-input">
            <div className="absolute inset-y-0 left-1/2 w-px bg-edge" />
            <span className="absolute top-2 left-2 font-mono text-[10px] text-faint">L</span>
            <span className="absolute top-2 right-2 font-mono text-[10px] text-faint">R</span>
            <span className="absolute right-2 bottom-2 font-mono text-[10px] text-faint">front</span>
            <span className="absolute top-7 right-2 font-mono text-[10px] text-faint">back</span>
            <div
              className="absolute h-2.5 -translate-x-1/2 -translate-y-1/2 rounded-pill bg-accent shadow-[0_0_16px_2px_var(--color-accent)] transition-[left,top,width] duration-200 ease-out"
              style={{
                left: `${(50 + balance * 40).toFixed(1)}%`,
                top: `${(distanceY * 100).toFixed(1)}%`,
                width: `${(clamp01(width) * 76).toFixed(1)}%`,
              }}
            />
          </div>

          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
            {stereo?.width_desc && <span>{stereo.width_desc}</span>}
            {stereo?.balance_desc && <span>{stereo.balance_desc}</span>}
            {stereo?.correlation_desc && <span>{stereo.correlation_desc}</span>}
          </div>
        </section>

        <section className="card p-5">
          <Eyebrow>Width by band</Eyebrow>
          <div className="mt-4 space-y-4">
            {bandRows.map(({ band, value }) => (
              <div key={band} className="space-y-1.5">
                <div className="flex items-baseline justify-between">
                  <span className="text-sm text-fg-secondary capitalize">{band}</span>
                  <span className="font-mono text-xs text-muted tabular-nums">{value.toFixed(2)}</span>
                </div>
                <div className="relative h-2 rounded-pill bg-surface-input">
                  <div
                    className={cn(
                      "absolute top-0 left-1/2 h-full -translate-x-1/2 rounded-pill",
                      band === stereo?.widest_band ? "bg-data-teal" : "bg-muted",
                    )}
                    style={{ width: `${clamp01(value) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="card p-5">
        <Eyebrow>Room · depth</Eyebrow>
        <StatGrid stats={roomStats} className="mt-4 grid-cols-2 sm:grid-cols-4" />
      </section>
    </div>
  );
}
