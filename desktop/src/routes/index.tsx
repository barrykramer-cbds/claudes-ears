import { useEffect } from "react";
import { z } from "zod";
import { createRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useShallow } from "zustand/react/shallow";
import { rootRoute } from "@/routes/root";
import { AppShell } from "@/components/shell/AppShell";
import { PipelineProgress } from "@/components/PipelineProgress";
import { Workspace } from "@/components/workspace/Workspace";
import { Button } from "@/components/ui/button";
import { fetchPerception } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { TabIdSchema, type TabId } from "@/lib/tabs";
import { useJobStore } from "@/stores/job-store";
import { libraryStore, useLibrary } from "@/stores/library-store";

function PaneCenter({ children }: { children: React.ReactNode }) {
  return <div className="grid min-h-0 flex-1 place-items-center overflow-auto p-6">{children}</div>;
}

function Home() {
  const { track: selectedId, tab } = indexRoute.useSearch();
  const navigate = indexRoute.useNavigate();
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
  const tracks = useLibrary((s) => s.tracks);

  const perception = useQuery({
    queryKey: queryKeys.perception.detail(jobId ?? "none"),
    queryFn: () => fetchPerception(jobId!),
    enabled: status === "done" && jobId !== null,
    staleTime: Infinity,
  });

  // A completed analysis enters the library and becomes the selection (lands on Voices).
  useEffect(() => {
    const doc = perception.data;
    if (status === "done" && doc) {
      libraryStore.getState().add(doc);
      void navigate({ search: (p) => ({ ...p, track: doc.track.id, tab: "voices" as TabId }) });
      reset();
    }
  }, [status, perception.data, navigate, reset]);

  const onAdd = async () => {
    const picked = await window.electron?.openAudioFile();
    void start(picked ?? "/music/dropped-sample.flac");
  };
  const onSelectTrack = (id: string) => void navigate({ search: (p) => ({ ...p, track: id }) });
  const onSelectTab = (id: TabId) => void navigate({ search: (p) => ({ ...p, tab: id }) });

  const selected =
    (selectedId ? tracks.find((t) => t.track.id === selectedId) : undefined) ?? tracks[0] ?? null;

  let main: React.ReactNode;
  if (status === "error") {
    main = (
      <PaneCenter>
        <div className="space-y-4 text-center">
          <div className="flex items-center justify-center gap-2">
            <span className="size-1.5 rounded-full bg-failed" aria-hidden />
            <p className="text-fg">{error ?? "Analysis failed."}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => void onAdd()}>
            Try another file
          </Button>
        </div>
      </PaneCenter>
    );
  } else if (status === "running" || status === "done") {
    main = (
      <div className="mx-auto w-full max-w-2xl flex-1 overflow-auto p-8">
        <PipelineProgress statuses={steps} activeStep={activeStep} />
      </div>
    );
  } else if (selected) {
    main = <Workspace doc={selected} tab={tab} onTabChange={onSelectTab} />;
  } else {
    main = (
      <PaneCenter>
        <p className="text-sm text-muted">No track yet — add one to begin.</p>
      </PaneCenter>
    );
  }

  return (
    <AppShell
      selectedId={selected?.track.id ?? null}
      onSelectTrack={onSelectTrack}
      onAdd={() => void onAdd()}
    >
      {main}
    </AppShell>
  );
}

export const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  validateSearch: z.object({ track: z.string().optional(), tab: TabIdSchema.default("voices") }),
  component: Home,
});
