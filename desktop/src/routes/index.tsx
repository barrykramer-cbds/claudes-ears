import { useEffect, useState } from "react";
import { z } from "zod";
import { createRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useShallow } from "zustand/react/shallow";
import { rootRoute } from "@/routes/root";
import { AppShell } from "@/components/shell/AppShell";
import { AddTrackModal } from "@/components/AddTrackModal";
import { PipelineProgress } from "@/components/PipelineProgress";
import { LibraryDashboard } from "@/components/dashboard/LibraryDashboard";
import { TrackSummaryPane } from "@/components/dashboard/TrackSummaryPane";
import { Workspace } from "@/components/workspace/Workspace";
import { Button } from "@/components/ui/button";
import { fetchPerception, type JobSource } from "@/lib/api";
import { libraryQueryOptions } from "@/lib/queries";
import { queryKeys } from "@/lib/query-keys";
import { mergeEntries } from "@/lib/library-entries";
import { TabIdSchema, type TabId } from "@/lib/tabs";
import { jobStore, useJobStore } from "@/stores/job-store";
import { libraryStore, useLibrary } from "@/stores/library-store";

function PaneCenter({ children }: { children: React.ReactNode }) {
  return <div className="grid min-h-0 flex-1 place-items-center overflow-auto p-6">{children}</div>;
}

function Home() {
  const { track: selectedId, tab } = indexRoute.useSearch();
  const navigate = indexRoute.useNavigate();
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const { status, jobId, steps, activeStep, error, reset } = useJobStore(
    useShallow((s) => ({
      status: s.status,
      jobId: s.jobId,
      steps: s.steps,
      activeStep: s.activeStep,
      error: s.error,
      reset: s.reset,
    })),
  );
  const docs = useLibrary((s) => s.tracks);
  const library = useQuery(libraryQueryOptions());

  const perception = useQuery({
    queryKey: queryKeys.perception.detail(jobId ?? "none"),
    queryFn: () => fetchPerception(jobId!),
    enabled: status === "done" && jobId !== null,
    staleTime: Infinity,
  });

  // A completed analysis enters the library, refreshes the index, and becomes the selection.
  useEffect(() => {
    const doc = perception.data;
    if (status === "done" && doc) {
      libraryStore.getState().add(doc);
      void queryClient.invalidateQueries({ queryKey: queryKeys.library.list });
      void navigate({ search: (p) => ({ ...p, track: doc.track.id, tab: "voices" as TabId }) });
      reset();
    }
  }, [status, perception.data, navigate, reset, queryClient]);

  const entries = mergeEntries(library.data?.items ?? [], docs);

  const onAdd = () => setAddOpen(true);
  const onSubmitSource = (source: JobSource) => {
    setAddOpen(false);
    void jobStore.getState().start(source);
  };
  const onSelectTrack = (id: string) => void navigate({ search: (p) => ({ ...p, track: id }) });
  const onSelectTab = (id: TabId) => void navigate({ search: (p) => ({ ...p, tab: id }) });

  const selectedDoc = selectedId ? docs.find((t) => t.track.id === selectedId) : undefined;
  const selectedEntry = selectedId ? entries.find((e) => e.id === selectedId) : undefined;

  let main: React.ReactNode;
  if (status === "error") {
    main = (
      <PaneCenter>
        <div className="space-y-4 text-center">
          <div className="flex items-center justify-center gap-2">
            <span className="size-1.5 rounded-full bg-failed" aria-hidden />
            <p className="text-fg">{error ?? "Analysis failed."}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onAdd}>
            Try another source
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
  } else if (selectedDoc) {
    main = <Workspace doc={selectedDoc} tab={tab} onTabChange={onSelectTab} />;
  } else if (selectedEntry) {
    main = <TrackSummaryPane entry={selectedEntry} />;
  } else if (entries.length > 0) {
    main = <LibraryDashboard entries={entries} onOpen={onSelectTrack} />;
  } else if (library.isPending) {
    main = (
      <PaneCenter>
        <p className="font-mono text-xs text-faint">reading the library…</p>
      </PaneCenter>
    );
  } else if (library.isError) {
    main = (
      <PaneCenter>
        <div className="space-y-4 text-center">
          <div className="flex items-center justify-center gap-2">
            <span className="size-1.5 rounded-full bg-failed" aria-hidden />
            <p className="text-fg">The analyzer isn't reachable — is the sidecar running?</p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => void library.refetch()}>
            Retry
          </Button>
        </div>
      </PaneCenter>
    );
  } else {
    main = (
      <PaneCenter>
        <p className="text-sm text-muted">No track yet — add one to begin.</p>
      </PaneCenter>
    );
  }

  return (
    <AppShell
      entries={entries}
      selectedId={selectedEntry?.id ?? null}
      onSelectTrack={onSelectTrack}
      onAdd={onAdd}
    >
      {main}
      <AddTrackModal open={addOpen} onClose={() => setAddOpen(false)} onSubmit={onSubmitSource} />
    </AppShell>
  );
}

export const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  validateSearch: z.object({ track: z.string().optional(), tab: TabIdSchema.default("voices") }),
  component: Home,
});
