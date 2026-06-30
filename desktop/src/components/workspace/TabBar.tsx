import { useLayoutEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { TabDef, TabId } from "@/lib/tabs";

interface TabBarProps {
  tabs: readonly TabDef[];
  active: TabId;
  onSelect: (id: TabId) => void;
}

export function TabBar({ tabs, active, onSelect }: TabBarProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRefs = useRef<Map<TabId, HTMLButtonElement>>(new Map());
  const [underline, setUnderline] = useState({ left: 0, width: 0 });

  // DOM geometry is owned by neither Query, the store, nor the router — measure it here.
  useLayoutEffect(() => {
    const btn = buttonRefs.current.get(active);
    const container = containerRef.current;
    if (!btn || !container) return;
    setUnderline({ left: btn.offsetLeft, width: btn.offsetWidth });
  }, [active, tabs]);

  return (
    <div
      ref={containerRef}
      role="tablist"
      aria-label="Analysis lenses"
      className="relative flex shrink-0 items-center gap-1 border-b border-border bg-surface px-3"
    >
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <div key={tab.id} className="flex items-center">
            {tab.id === "library" && <span className="px-1 text-faint">·</span>}
            <button
              ref={(el) => {
                if (el) buttonRefs.current.set(tab.id, el);
                else buttonRefs.current.delete(tab.id);
              }}
              role="tab"
              aria-selected={isActive}
              tabIndex={isActive ? 0 : -1}
              onClick={() => onSelect(tab.id)}
              className={cn(
                "rounded-button px-3 py-2.5 text-sm font-medium transition-colors duration-150 ease-out outline-none focus-visible:text-fg",
                isActive ? "text-fg" : "text-muted hover:text-fg-secondary",
              )}
            >
              {tab.label}
            </button>
          </div>
        );
      })}
      <div
        className="tab-underline absolute bottom-0 h-0.5 rounded-pill bg-accent"
        style={{ left: underline.left, width: underline.width }}
        aria-hidden
      />
    </div>
  );
}
