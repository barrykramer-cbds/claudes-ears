import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { RouterProvider, createRouter, createMemoryHistory } from "@tanstack/react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { routeTree } from "@/router";
import { fetchLibrary } from "@/lib/api";
import { libraryStore } from "@/stores/library-store";
import { jobStore } from "@/stores/job-store";

const page = {
  items: [
    {
      track_id: "ghost_note",
      title: "Ghost Note",
      artist: "The Levee",
      key: "A",
      mode: "minor",
      tempo: 96.4,
      duration_s: 228,
      ai_verdict: "human",
      analyzed_at: "2026-06-30T12:00:00Z",
      extra_server_field: "tolerated",
    },
  ],
  total: 1,
  page: 1,
  limit: 200,
};

function stubLibraryFetch() {
  vi.mocked(globalThis.fetch).mockImplementation((input) => {
    const url = input instanceof Request ? input.url : String(input);
    if (url.includes("/library")) {
      return Promise.resolve(new Response(JSON.stringify(page), { status: 200 }));
    }
    return Promise.reject(new Error("unexpected fetch"));
  });
}

describe("library hydrate", () => {
  beforeEach(() => {
    libraryStore.getState().clear();
    jobStore.getState().reset();
    stubLibraryFetch();
  });

  it("parses the GET /library page, tolerating extra fields", async () => {
    const result = await fetchLibrary();
    expect(result.total).toBe(1);
    expect(result.items[0]).toMatchObject({ track_id: "ghost_note", tempo: 96.4 });
  });

  it("renders indexed tracks on the dashboard after hydrate", async () => {
    const router = createRouter({
      routeTree,
      history: createMemoryHistory({ initialEntries: ["/"] }),
    });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
    expect(await screen.findByText(/1 track analyzed/)).toBeInTheDocument();
    expect(screen.getAllByText("Ghost Note").length).toBeGreaterThan(0);
    expect(screen.getByText("96 bpm")).toBeInTheDocument();
  });
});
