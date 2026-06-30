import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  dotClassName?: string;
}

export function Badge({ children, dotClassName }: BadgeProps) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-pill border border-border bg-surface-raised px-2.5 py-1 text-xs font-medium text-fg-secondary">
      {dotClassName && <span className={cn("size-1.5 rounded-full", dotClassName)} aria-hidden />}
      {children}
    </span>
  );
}
