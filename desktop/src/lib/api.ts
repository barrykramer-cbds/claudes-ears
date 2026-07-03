import { z } from "zod";
import { env } from "@/env";
import { randomId } from "@/lib/utils";
import { mockPerception } from "@/mock/perception";
import { mockProgressStream } from "@/mock/sse";
import {
  JobSchema,
  PerceptionDocumentSchema,
  ProgressEventSchema,
  TrackPageSchema,
  type Job,
  type PerceptionDocument,
  type ProgressEvent,
  type TrackPage,
} from "@/lib/schemas";

// POST /jobs takes exactly one source: a sidecar-local file or a URL the sidecar downloads.
export type JobSource = { audio_path: string } | { source_url: string };

export function sourceLabel(source: JobSource): string {
  return "audio_path" in source ? source.audio_path : source.source_url;
}

class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const res = await fetch(`${env.VITE_API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new ApiError(`${path} failed`, res.status);
  return schema.parse(await res.json());
}

export interface ProgressHandlers {
  onEvent: (event: ProgressEvent) => void;
  onComplete: () => void;
  onError?: (error: Error) => void;
}

export function createJob(source: JobSource): Promise<Job> {
  if (env.VITE_USE_MOCK) {
    return Promise.resolve(
      JobSchema.parse({
        id: randomId(),
        source_path: sourceLabel(source),
        status: "running",
        current_step: null,
        step_index: 0,
        step_total: 21,
        error: null,
        created_at: new Date().toISOString(),
        finished_at: null,
      }),
    );
  }
  return request("/jobs", JobSchema, {
    method: "POST",
    body: JSON.stringify(source),
  });
}

export function fetchLibrary(): Promise<TrackPage> {
  if (env.VITE_USE_MOCK) {
    const t = mockPerception.track;
    return Promise.resolve(
      TrackPageSchema.parse({
        items: [{ track_id: t.id, title: t.title, artist: t.artist }],
        total: 1,
        page: 1,
        limit: 200,
      }),
    );
  }
  return request("/library?page=1&limit=200", TrackPageSchema);
}

export function fetchPerception(jobId: string): Promise<PerceptionDocument> {
  if (env.VITE_USE_MOCK) return Promise.resolve(PerceptionDocumentSchema.parse(mockPerception));
  return request(`/jobs/${jobId}/perception`, PerceptionDocumentSchema);
}

export function subscribeProgress(jobId: string, handlers: ProgressHandlers): () => void {
  if (env.VITE_USE_MOCK) {
    return mockProgressStream(jobId, handlers.onEvent, handlers.onComplete);
  }

  const source = new EventSource(`${env.VITE_API_BASE_URL}/jobs/${jobId}/events`);
  source.onmessage = (msg) => {
    const parsed = ProgressEventSchema.safeParse(JSON.parse(msg.data as string));
    if (parsed.success) handlers.onEvent(parsed.data);
    else handlers.onError?.(new ApiError("malformed progress event"));
  };
  source.addEventListener("done", () => {
    source.close();
    handlers.onComplete();
  });
  source.onerror = () => {
    source.close();
    handlers.onError?.(new ApiError("progress stream error"));
  };
  return () => source.close();
}

export { ApiError };
