import { useEffect, useRef } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TitlebarProps {
  query: string;
  onQuery: (q: string) => void;
  onAdd: () => void;
}

export function Titlebar({ query, onQuery, onAdd }: TitlebarProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  // Global ⌘K focuses library search — a window shortcut with no store/router owner.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <header className="flex items-center justify-between border-b border-border bg-surface px-3.5">
      <div className="flex items-center gap-2 text-sm font-semibold text-fg-secondary">
        <span
          className="size-3.5 rounded-full border-2 border-accent border-r-transparent"
          aria-hidden
        />
        Claude's Ears
      </div>

      <div className="flex items-center gap-2.5">
        <div className="relative">
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => onQuery(e.target.value)}
            placeholder="Search library"
            aria-label="Search library"
            className="w-56 rounded-button border border-border bg-surface-input py-1.5 pr-12 pl-3 text-xs text-fg-secondary outline-none placeholder:text-muted focus-visible:border-border-strong"
          />
          <kbd className="pointer-events-none absolute top-1/2 right-2 -translate-y-1/2 rounded border border-border px-1.5 py-px font-mono text-[10px] text-faint">
            ⌘K
          </kbd>
        </div>
        <Button size="sm" onClick={onAdd}>
          <Plus className="size-3.5" aria-hidden />
          Add track
        </Button>
      </div>
    </header>
  );
}
