import { useRef } from "react";
import { useShallow } from "zustand/react/shallow";
import { usePlayback } from "@/stores/playback-store";
import { cn } from "@/lib/utils";

interface TimeFieldProps {
  children: React.ReactNode;
  className?: string;
}

// A time-aligned scrub surface: hovering or clicking anywhere moves the shared
// playhead/guide, so every time-axis view stays locked to the same x.
export function TimeField({ children, className }: TimeFieldProps) {
  const ref = useRef<HTMLDivElement>(null);
  const { positionPct, hoverPct, seek, hover } = usePlayback(
    useShallow((s) => ({
      positionPct: s.positionPct,
      hoverPct: s.hoverPct,
      seek: s.seek,
      hover: s.hover,
    })),
  );

  const pctAt = (clientX: number): number => {
    const el = ref.current;
    if (!el) return 0;
    const r = el.getBoundingClientRect();
    return (clientX - r.left) / r.width;
  };

  return (
    <div
      ref={ref}
      onPointerMove={(e) => hover(pctAt(e.clientX))}
      onPointerLeave={() => hover(null)}
      onClick={(e) => seek(pctAt(e.clientX))}
      className={cn("relative cursor-pointer", className)}
    >
      {children}
      {hoverPct !== null && (
        <div
          className="pointer-events-none absolute inset-y-0 z-10 w-px bg-fg/15"
          style={{ left: `${hoverPct * 100}%` }}
          aria-hidden
        />
      )}
      <div
        className="scrub-playhead pointer-events-none absolute inset-y-0 z-10 w-px bg-accent/50"
        style={{ left: `${positionPct * 100}%` }}
        aria-hidden
      />
    </div>
  );
}
