import { useRef, useState } from "react";
import { useShallow } from "zustand/react/shallow";
import { usePlayback } from "@/stores/playback-store";
import { formatClock } from "@/lib/utils";

interface TimeScrubberProps {
  durationS: number;
}

export function TimeScrubber({ durationS }: TimeScrubberProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);
  const { positionPct, hoverPct, seek, hover } = usePlayback(
    useShallow((s) => ({
      positionPct: s.positionPct,
      hoverPct: s.hoverPct,
      seek: s.seek,
      hover: s.hover,
    })),
  );

  const pctAt = (clientX: number): number => {
    const el = trackRef.current;
    if (!el) return 0;
    const r = el.getBoundingClientRect();
    return (clientX - r.left) / r.width;
  };

  const guide = dragging ? positionPct : hoverPct;

  return (
    <div
      ref={trackRef}
      role="slider"
      aria-label="Track position"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(positionPct * 100)}
      tabIndex={0}
      onPointerDown={(e) => {
        e.currentTarget.setPointerCapture(e.pointerId);
        setDragging(true);
        seek(pctAt(e.clientX));
      }}
      onPointerMove={(e) => (dragging ? seek(pctAt(e.clientX)) : hover(pctAt(e.clientX)))}
      onPointerUp={(e) => {
        e.currentTarget.releasePointerCapture(e.pointerId);
        setDragging(false);
      }}
      onPointerLeave={() => hover(null)}
      className="group relative h-5 shrink-0 cursor-pointer touch-none border-b border-border bg-surface select-none"
    >
      <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-border" />
      <div
        className="absolute top-1/2 left-0 h-px -translate-y-1/2 bg-accent/40"
        style={{ width: `${positionPct * 100}%` }}
      />
      {guide !== null && (
        <div
          className="pointer-events-none absolute inset-y-0 w-px bg-fg/15"
          style={{ left: `${guide * 100}%` }}
        >
          <span className="absolute -top-0 left-1 -translate-y-full rounded-button bg-surface-raised px-1.5 py-0.5 font-mono text-[10px] text-muted">
            {formatClock(guide * durationS)}
          </span>
        </div>
      )}
      <div
        className="scrub-playhead absolute top-1/2 h-3 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-pill bg-accent"
        data-dragging={dragging}
        style={{ left: `${positionPct * 100}%` }}
      />
    </div>
  );
}
