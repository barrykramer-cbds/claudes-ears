import { PIPELINE_STEPS } from "@/lib/pipeline-steps";
import type { ProgressEvent } from "@/lib/schemas";

const SKIPPED = new Set(["semantic_lyrics"]);

// Drives the mock through started→completed (or skipped) for all 21 steps, then resolves.
export function mockProgressStream(
  jobId: string,
  onEvent: (event: ProgressEvent) => void,
  onComplete: () => void,
  stepMs = 220,
): () => void {
  const total = PIPELINE_STEPS.length;
  const timers: ReturnType<typeof setTimeout>[] = [];
  let cancelled = false;

  PIPELINE_STEPS.forEach((step, i) => {
    const skipped = SKIPPED.has(step.name);
    const base = i * stepMs;
    timers.push(
      setTimeout(() => {
        if (cancelled) return;
        onEvent({
          job_id: jobId,
          step: step.name,
          index: i + 1,
          total,
          status: skipped ? "skipped" : "started",
        });
      }, base),
    );
    if (!skipped) {
      timers.push(
        setTimeout(() => {
          if (cancelled) return;
          onEvent({ job_id: jobId, step: step.name, index: i + 1, total, status: "completed" });
        }, base + stepMs * 0.6),
      );
    }
  });

  timers.push(
    setTimeout(() => {
      if (!cancelled) onComplete();
    }, total * stepMs + stepMs),
  );

  return () => {
    cancelled = true;
    timers.forEach(clearTimeout);
  };
}
