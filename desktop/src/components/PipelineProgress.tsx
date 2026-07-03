import { CheckCircle2, Circle, Loader2, MinusCircle, XCircle } from "lucide-react";
import { PIPELINE_STEPS, type PipelineStep } from "@/lib/pipeline-steps";
import type { StepStatus } from "@/lib/schemas";
import { cn } from "@/lib/utils";

const KNOWN = new Set(PIPELINE_STEPS.map((s) => s.name));
const EXTRA_LABELS: Record<string, string> = { download: "Downloading audio" };

// Steps the sidecar emits that aren't in the pinned 21 (e.g. a YouTube "download"
// pre-step) render ahead of the pipeline instead of being dropped or crashing.
function extraSteps(statuses: Record<string, StepStatus>): PipelineStep[] {
  return Object.keys(statuses)
    .filter((name) => !KNOWN.has(name))
    .map((name) => ({
      name,
      label: EXTRA_LABELS[name] ?? name.replaceAll("_", " "),
      phase: "Source",
    }));
}

interface PipelineProgressProps {
  statuses: Record<string, StepStatus>;
  activeStep: string | null;
}

const DONE = new Set<StepStatus>(["completed", "skipped"]);

function StatusIcon({ status }: { status: StepStatus | undefined }) {
  if (status === "completed")
    return <CheckCircle2 className="size-4 text-done motion-safe:animate-[pop_180ms_ease-out]" aria-hidden />;
  if (status === "skipped") return <MinusCircle className="size-4 text-skipped" aria-hidden />;
  if (status === "failed") return <XCircle className="size-4 text-failed" aria-hidden />;
  if (status === "started")
    return <Loader2 className="size-4 text-active motion-safe:animate-spin" aria-hidden />;
  return <Circle className="size-4 text-faint/40" aria-hidden />;
}

export function PipelineProgress({ statuses, activeStep }: PipelineProgressProps) {
  const steps = [...extraSteps(statuses), ...PIPELINE_STEPS];
  const total = steps.length;
  const done = steps.filter((s) => DONE.has(statuses[s.name] as StepStatus)).length;
  const pct = Math.round((done / total) * 100);

  return (
    <section aria-label="Analysis progress" className="space-y-5">
      <div className="space-y-2">
        <div className="flex items-baseline justify-between text-sm">
          <span className="font-medium text-fg">Listening</span>
          <span className="tabular-nums text-muted">
            {done} / {total}
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-surface-raised">
          <div
            className="h-full rounded-full bg-accent transition-[width] duration-300 ease-out"
            style={{ width: `${pct}%` }}
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>

      <ul className="space-y-0.5">
        {steps.map((step, i) => {
          const status = statuses[step.name];
          const isActive = activeStep === step.name;
          const header = steps[i - 1]?.phase !== step.phase ? step.phase : null;
          return (
            <li key={step.name}>
              {header && (
                <p className="px-2 pt-3 pb-1 text-xs font-medium tracking-wide text-faint uppercase">
                  {header}
                </p>
              )}
              <div
                style={{ animationDelay: `${Math.min(i * 24, 360)}ms` }}
                className={cn(
                  "flex items-center gap-3 rounded-md px-2 py-1.5 motion-safe:animate-[step-in_240ms_ease-out_backwards]",
                  isActive && "bg-surface-raised",
                )}
              >
                <StatusIcon status={status} />
                <span
                  className={cn(
                    "text-sm transition-colors duration-200",
                    DONE.has(status as StepStatus)
                      ? "text-muted"
                      : isActive
                        ? "text-fg"
                        : "text-faint",
                  )}
                >
                  {step.label}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
