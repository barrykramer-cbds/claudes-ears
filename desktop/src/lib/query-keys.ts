export const queryKeys = {
  jobs: {
    all: ["jobs"] as const,
    detail: (id: string) => ["jobs", id] as const,
  },
  perception: {
    detail: (jobId: string) => ["perception", jobId] as const,
  },
} as const;
