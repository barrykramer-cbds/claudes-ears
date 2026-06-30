import { createRoute, useRouter } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useShallow } from "zustand/react/shallow";
import { rootRoute } from "@/routes/root";
import { DropZone } from "@/components/DropZone";
import { PipelineProgress } from "@/components/PipelineProgress";
import { PerceptionSummary } from "@/components/PerceptionSummary";
import { Button } from "@/components/ui/button";
import { fetchPerception } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useJobStore } from "@/stores/job-store";

function Home() {
  const { invalidate } = useRouter();
  const { status, jobId, steps, activeStep, error, start, reset } = useJobStore(
    useShallow((s) => ({
      status: s.status,
      jobId: s.jobId,
      steps: s.steps,
      activeStep: s.activeStep,
      error: s.error,
      start: s.start,
      reset: s.reset,
    })),
  );

  const perception = useQuery({
    queryKey: queryKeys.perception.detail(jobId ?? "none"),
    queryFn: () => fetchPerception(jobId!),
    enabled: status === "done" && jobId !== null,
    staleTime: Infinity,
  });

  if (status === "idle") return <DropZone onPick={(p) => void start(p)} />;

  if (status === "error")
    return (
      <div className="space-y-4">
        <p className="text-failed">{error ?? "Analysis failed."}</p>
        <Button variant="ghost" size="sm" onClick={reset}>
          Try another file
        </Button>
      </div>
    );

  if (status === "done" && perception.data)
    return (
      <PerceptionSummary
        doc={perception.data}
        onReset={() => {
          reset();
          void invalidate();
        }}
      />
    );

  return <PipelineProgress statuses={steps} activeStep={activeStep} />;
}

export const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: Home,
});
