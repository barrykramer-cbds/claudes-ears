import { createStore } from "zustand/vanilla";
import { useStore } from "zustand";
import { createJob, subscribeProgress } from "@/lib/api";
import type { StepStatus } from "@/lib/schemas";

export type AnalysisStatus = "idle" | "running" | "done" | "error";

interface JobState {
  status: AnalysisStatus;
  jobId: string | null;
  sourcePath: string | null;
  steps: Record<string, StepStatus>;
  activeStep: string | null;
  error: string | null;
  start: (sourcePath: string) => Promise<void>;
  reset: () => void;
}

let unsubscribe: (() => void) | null = null;

const initial = {
  status: "idle" as AnalysisStatus,
  jobId: null,
  sourcePath: null,
  steps: {} as Record<string, StepStatus>,
  activeStep: null,
  error: null,
};

export const jobStore = createStore<JobState>((set, get) => ({
  ...initial,

  reset: () => {
    unsubscribe?.();
    unsubscribe = null;
    set({ ...initial });
  },

  start: async (sourcePath) => {
    get().reset();
    set({ status: "running", sourcePath });
    try {
      const job = await createJob(sourcePath);
      set({ jobId: job.id });
      unsubscribe = subscribeProgress(job.id, {
        onEvent: (event) =>
          set((s) => ({
            steps: { ...s.steps, [event.step]: event.status },
            activeStep: event.status === "started" ? event.step : s.activeStep,
          })),
        onComplete: () => set({ status: "done", activeStep: null }),
        onError: (err) => set({ status: "error", error: err.message }),
      });
    } catch (err) {
      set({ status: "error", error: err instanceof Error ? err.message : "Failed to start" });
    }
  },
}));

export function useJobStore<T>(selector: (state: JobState) => T): T {
  return useStore(jobStore, selector);
}
