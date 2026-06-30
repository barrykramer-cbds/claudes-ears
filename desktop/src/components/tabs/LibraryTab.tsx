import { Eyebrow } from "@/components/ui/eyebrow";
import { cn, formatClock } from "@/lib/utils";
import type { PerceptionDocument } from "@/lib/schemas";

interface LibraryTabProps {
  doc: PerceptionDocument;
}

interface GenomeDim {
  key: keyof NonNullable<PerceptionDocument["genome"]>;
  label: string;
  norm: number;
  hue: string;
}

const GENOME_DIMS: GenomeDim[] = [
  { key: "vocal_pitch", label: "vocal pitch", norm: 400, hue: "bg-data-orange" },
  { key: "vocal_range", label: "vocal range", norm: 24, hue: "bg-data-orange" },
  { key: "vocal_entropy", label: "vocal entropy", norm: 1, hue: "bg-data-orange" },
  { key: "vocal_breathiness", label: "breathiness", norm: 1, hue: "bg-data-orange" },
  { key: "vocal_presence", label: "vocal presence", norm: 1, hue: "bg-data-orange" },
  { key: "drum_tempo", label: "drum tempo", norm: 200, hue: "bg-data-blue" },
  { key: "drum_regularity", label: "drum regularity", norm: 1, hue: "bg-data-blue" },
  { key: "drum_density", label: "drum density", norm: 8, hue: "bg-data-blue" },
  { key: "drum_kick_pct", label: "kick share", norm: 1, hue: "bg-data-blue" },
  { key: "bass_movement", label: "bass movement", norm: 1, hue: "bg-data-green" },
  { key: "texture_centroid", label: "texture centroid", norm: 4000, hue: "bg-data-yellow" },
  { key: "texture_harmonic", label: "texture harmonic", norm: 1, hue: "bg-data-yellow" },
];

export function LibraryTab({ doc }: LibraryTabProps) {
  const { track, genome } = doc;
  const key = doc.harmony?.theory ? `${doc.harmony.theory.key} ${doc.harmony.theory.mode}` : null;
  const bpm = doc.rhythm?.groove ? `${Math.round(doc.rhythm.groove.tempo)} BPM` : null;

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6 motion-safe:animate-[step-in_240ms_ease-out]">
      <p className="text-sm text-muted">
        One track analyzed. The library and its sonic twins fill in as you listen to more.
      </p>

      <div className="grid gap-4 md:grid-cols-2">
        <section className="card p-5">
          <Eyebrow>Tracks</Eyebrow>
          <ul className="mt-4 space-y-2">
            <li className="flex items-center justify-between rounded-button border border-accent/40 bg-accent-tint/40 px-3 py-2.5">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-fg">{track.title ?? track.id}</p>
                <p className="truncate text-xs text-muted">{track.artist ?? "Unknown artist"}</p>
              </div>
              <span className="shrink-0 font-mono text-xs text-muted">
                {[key, bpm, track.duration_s ? formatClock(track.duration_s) : null]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </li>
            {[0, 1, 2].map((i) => (
              <li
                key={i}
                className="flex items-center gap-3 rounded-button border border-dashed border-border px-3 py-2.5"
              >
                <span className="h-2 w-2 rounded-full bg-surface-hover" aria-hidden />
                <span className="text-sm text-faint">Awaiting analysis</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="card flex flex-col p-5">
          <Eyebrow>Sonic twins</Eyebrow>
          {genome ? (
            <>
              <p className="mt-4 text-xs text-muted">This track's genome</p>
              <div className="mt-3 flex h-24 items-end gap-1">
                {GENOME_DIMS.map((d) => {
                  const raw = genome[d.key];
                  const h = Math.min(1, Math.max(0.04, raw / d.norm));
                  return (
                    <div
                      key={d.key}
                      className={cn("flex-1 rounded-t-sm", d.hue)}
                      style={{ height: `${h * 100}%`, opacity: 0.7 }}
                      title={`${d.label}: ${raw}`}
                    />
                  );
                })}
              </div>
            </>
          ) : (
            <p className="mt-4 text-sm text-muted">No genome vector for this track.</p>
          )}
          <p className="mt-auto pt-6 text-sm text-faint">
            Nearest twins surface once more tracks share this fingerprint.
          </p>
        </section>
      </div>
    </div>
  );
}
