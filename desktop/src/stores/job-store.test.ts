import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ProgressHandlers } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  createJob: vi.fn(() =>
    Promise.resolve({
      id: "job1",
      source_path: "/music/x.flac",
      status: "running",
      current_step: null,
      step_index: 0,
      step_total: 21,
      error: null,
      created_at: "2026-06-30T00:00:00Z",
      finished_at: null,
    }),
  ),
  subscribeProgress: vi.fn((jobId: string, h: ProgressHandlers) => {
    h.onEvent({ job_id: jobId, step: "separation", index: 1, total: 21, status: "started" });
    h.onEvent({ job_id: jobId, step: "separation", index: 1, total: 21, status: "completed" });
    h.onEvent({ job_id: jobId, step: "semantic_lyrics", index: 19, total: 21, status: "skipped" });
    h.onComplete();
    return () => undefined;
  }),
}));

const { jobStore } = await import("@/stores/job-store");

describe("jobStore", () => {
  beforeEach(() => jobStore.getState().reset());

  it("drives steps to done from a source path", async () => {
    await jobStore.getState().start("/music/x.flac");
    const state = jobStore.getState();
    expect(state.status).toBe("done");
    expect(state.jobId).toBe("job1");
    expect(state.steps.separation).toBe("completed");
    expect(state.steps.semantic_lyrics).toBe("skipped");
    expect(state.activeStep).toBeNull();
  });

  it("reports failure when createJob throws", async () => {
    const api = await import("@/lib/api");
    vi.mocked(api.createJob).mockRejectedValueOnce(new Error("sidecar down"));
    await jobStore.getState().start("/music/x.flac");
    expect(jobStore.getState().status).toBe("error");
    expect(jobStore.getState().error).toBe("sidecar down");
  });

  it("clears prior state on reset", async () => {
    await jobStore.getState().start("/music/x.flac");
    jobStore.getState().reset();
    expect(jobStore.getState().status).toBe("idle");
    expect(jobStore.getState().steps).toEqual({});
  });
});
