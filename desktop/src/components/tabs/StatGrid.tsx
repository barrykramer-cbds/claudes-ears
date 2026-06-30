import { cn } from "@/lib/utils";

export interface Stat {
  label: string;
  value: string;
  unit?: string;
}

interface StatGridProps {
  stats: Stat[];
  className?: string;
}

export function StatGrid({ stats, className }: StatGridProps) {
  return (
    <dl className={cn("grid gap-px overflow-hidden rounded-button bg-border", className)}>
      {stats.map((s) => (
        <div key={s.label} className="bg-surface px-4 py-3">
          <dt className="font-mono text-[10px] tracking-[0.12em] text-faint uppercase">{s.label}</dt>
          <dd className="mt-1 font-mono text-lg text-fg tabular-nums">
            {s.value}
            {s.unit && <span className="ml-0.5 text-sm text-muted">{s.unit}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}
