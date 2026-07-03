import { useShallow } from "zustand/react/shallow";
import { Loader2, PanelLeft, PanelLeftClose, Plus } from "lucide-react";
import { useJobStore } from "@/stores/job-store";
import { VOICE_BG } from "@/components/tabs/voice-taxonomy";
import type { LibraryEntry } from "@/lib/library-entries";
import { cn, formatClock } from "@/lib/utils";

interface LibrarySidebarProps {
  entries: LibraryEntry[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAdd: () => void;
  query: string;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

function subtitle(entry: LibraryEntry): string {
  const duration = entry.durationS != null ? formatClock(entry.durationS) : null;
  return [entry.keyMode, duration].filter(Boolean).join(" · ");
}

// A URL source shows as its trimmed address; a path shows as its basename.
const sourceName = (p: string) =>
  /^https?:\/\//.test(p) ? p.replace(/^https?:\/\/(www\.)?/, "") : (p.split(/[\\/]/).pop() ?? p);

export function LibrarySidebar({
  entries,
  selectedId,
  onSelect,
  onAdd,
  query,
  collapsed,
  onToggleCollapse,
}: LibrarySidebarProps) {
  const { status, sourcePath } = useJobStore(
    useShallow((s) => ({ status: s.status, sourcePath: s.sourcePath })),
  );
  const analyzing = (status === "running" || status === "done") && sourcePath !== null;

  const q = query.trim().toLowerCase();
  const filtered = q
    ? entries.filter((e) => `${e.title} ${e.artist ?? ""}`.toLowerCase().includes(q))
    : entries;

  if (collapsed) {
    return (
      <aside className="flex flex-col items-center gap-3 border-r border-border bg-surface py-3">
        <button
          onClick={onToggleCollapse}
          aria-label="Expand library"
          className="rounded-button p-1.5 text-muted hover:bg-surface-hover hover:text-fg"
        >
          <PanelLeft className="size-4" aria-hidden />
        </button>
        <button
          onClick={onAdd}
          aria-label="Add track"
          className="rounded-button p-1.5 text-muted hover:bg-surface-hover hover:text-fg"
        >
          <Plus className="size-4" aria-hidden />
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex min-h-0 flex-col border-r border-border bg-surface">
      <div className="flex items-center justify-between py-3 pr-2 pl-4">
        <h2 className="font-mono text-[10px] tracking-[0.18em] text-faint uppercase">Library</h2>
        <button
          onClick={onToggleCollapse}
          aria-label="Collapse library"
          className="rounded-button p-1 text-muted hover:bg-surface-hover hover:text-fg"
        >
          <PanelLeftClose className="size-4" aria-hidden />
        </button>
      </div>

      <nav aria-label="Analyzed tracks" className="min-h-0 flex-1 space-y-0.5 overflow-auto px-2">
        {analyzing && sourcePath && (
          <div className="flex items-center gap-2.5 rounded-button px-2.5 py-2 text-sm text-fg-secondary">
            <Loader2 className="size-3.5 shrink-0 text-active motion-safe:animate-spin" aria-hidden />
            <div className="min-w-0">
              <p className="truncate font-medium">{sourceName(sourcePath)}</p>
              <p className="font-mono text-[10px] text-faint">analyzing…</p>
            </div>
          </div>
        )}

        {filtered.map((entry) => {
          const active = entry.id === selectedId;
          return (
            <button
              key={entry.id}
              onClick={() => onSelect(entry.id)}
              aria-current={active ? "true" : undefined}
              className={cn(
                "flex w-full items-center gap-2.5 rounded-button border-l-2 px-2.5 py-2 text-left text-sm transition-colors duration-150 ease-out",
                active
                  ? "border-accent bg-surface-raised text-fg"
                  : "border-transparent text-fg-secondary hover:bg-surface-hover",
              )}
            >
              <span
                className={cn(
                  "size-1.5 shrink-0 rounded-full",
                  entry.voice ? VOICE_BG[entry.voice] : "bg-muted",
                )}
                aria-hidden
              />
              <span className="min-w-0">
                <span className="block truncate font-medium">{entry.title}</span>
                <span className="block truncate font-mono text-[10px] text-faint">
                  {subtitle(entry)}
                </span>
              </span>
            </button>
          );
        })}

        {filtered.length === 0 && !analyzing && (
          <p className="px-2.5 py-3 text-sm text-faint">{q ? "No matches." : "No tracks yet."}</p>
        )}
      </nav>

      <div className="border-t border-border p-2.5">
        <button
          onClick={onAdd}
          className="flex w-full items-center gap-2 rounded-button border border-dashed border-border-strong px-2.5 py-2 text-sm text-muted transition-colors hover:border-faint hover:text-fg"
        >
          <Plus className="size-3.5" aria-hidden />
          Add track
        </button>
      </div>
    </aside>
  );
}
