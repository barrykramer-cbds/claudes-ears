import { Eyebrow } from "@/components/ui/eyebrow";
import { VOICE_BG } from "@/components/tabs/voice-taxonomy";
import type { LibraryEntry } from "@/lib/library-entries";
import { cn, formatClock } from "@/lib/utils";

interface LibraryDashboardProps {
  entries: LibraryEntry[];
  onOpen: (id: string) => void;
}

function verdictTone(verdict: string | null): string {
  const v = verdict?.toLowerCase() ?? "";
  if (v.includes("human")) return "bg-done";
  if (v.includes("ai") || v.includes("synthetic")) return "bg-failed";
  return "bg-faint";
}

function analyzedDate(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function LibraryDashboard({ entries, onOpen }: LibraryDashboardProps) {
  return (
    <div className="min-h-0 flex-1 overflow-auto p-6">
      <div className="mx-auto max-w-4xl space-y-4">
        <div className="flex items-baseline justify-between">
          <Eyebrow>Library</Eyebrow>
          <span className="font-mono text-[11px] text-faint tabular-nums">
            {entries.length} {entries.length === 1 ? "track" : "tracks"} analyzed
          </span>
        </div>

        <ul className="grid grid-cols-[repeat(auto-fill,minmax(15rem,1fr))] gap-3">
          {entries.map((e, i) => (
            <li key={e.id} className="min-w-0">
              <button
                onClick={() => onOpen(e.id)}
                style={{ animationDelay: `${Math.min(i * 30, 240)}ms` }}
                className={cn(
                  "card group w-full p-4 text-left transition-[transform,border-color] duration-150 ease-out",
                  "hover:border-border-strong active:scale-[0.99]",
                  "motion-safe:animate-[step-in_240ms_ease-out_backwards]",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 space-y-0.5">
                    <p className="flex items-center gap-2 text-sm font-medium text-fg">
                      <span
                        title={e.verdict ?? undefined}
                        className={cn(
                          "size-1.5 shrink-0 rounded-full",
                          e.voice ? VOICE_BG[e.voice] : verdictTone(e.verdict),
                        )}
                        aria-hidden
                      />
                      <span className="truncate">{e.title}</span>
                    </p>
                    <p className="truncate pl-3.5 text-xs text-muted">
                      {[e.artist, e.era].filter(Boolean).join(" · ") || " "}
                    </p>
                  </div>
                  {e.keyMode && (
                    <span className="shrink-0 font-mono text-lg leading-none text-faint transition-colors duration-150 group-hover:text-fg-secondary">
                      {e.keyMode.replace(/ (major|minor)/i, (m) => (m.includes("minor") ? "m" : ""))}
                    </span>
                  )}
                </div>

                <p className="mt-3 flex items-baseline gap-3 border-t border-border pt-2.5 font-mono text-[11px] text-faint tabular-nums">
                  {e.tempo != null && <span>{Math.round(e.tempo)} bpm</span>}
                  {e.durationS != null && <span>{formatClock(e.durationS)}</span>}
                  {analyzedDate(e.analyzedAt) && (
                    <span className="ml-auto">{analyzedDate(e.analyzedAt)}</span>
                  )}
                </p>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
