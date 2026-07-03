import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createRouter, createMemoryHistory } from "@tanstack/react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { routeTree } from "@/router";
import { libraryStore } from "@/stores/library-store";
import { jobStore } from "@/stores/job-store";
import { mockPerception } from "@/mock/perception";
import type { PerceptionDocument } from "@/lib/schemas";

const tokyo: PerceptionDocument = {
  ...mockPerception,
  track: { ...mockPerception.track, id: "tokyo_live", title: "Tokyo, Live" },
};

function renderApp() {
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

function seedLibrary() {
  libraryStore.getState().add(mockPerception);
  libraryStore.getState().add(tokyo);
}

const sidebar = async () =>
  within(await screen.findByRole("navigation", { name: "Analyzed tracks" }));

describe("app shell", () => {
  beforeEach(() => {
    libraryStore.getState().clear();
    jobStore.getState().reset();
  });

  it("shows a quiet empty state in the main pane when the library is empty", async () => {
    renderApp();
    expect(await screen.findByText(/No track yet — add one to begin/)).toBeInTheDocument();
    expect(screen.getByText(/No tracks yet/)).toBeInTheDocument();
  });

  it("shows the dashboard when tracks exist and none is selected", async () => {
    seedLibrary();
    renderApp();
    expect(await screen.findByText(/2 tracks analyzed/)).toBeInTheDocument();
    expect((await sidebar()).getByRole("button", { name: /Tokyo, Live/ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument();
  });

  it("opens a track's workspace from a dashboard card", async () => {
    seedLibrary();
    renderApp();
    const user = userEvent.setup();
    const list = within(await screen.findByRole("list"));
    await user.click(list.getByRole("button", { name: /The Weight/ }));
    expect(await screen.findByRole("heading", { level: 1, name: /The Weight/ })).toBeInTheDocument();
    expect(screen.getByText("Vocal relationship · density over time")).toBeInTheDocument();
  });

  it("swaps the workspace when a sidebar track is selected", async () => {
    seedLibrary();
    renderApp();
    const user = userEvent.setup();
    await user.click((await sidebar()).getByRole("button", { name: /Tokyo, Live/ }));
    await screen.findByRole("heading", { level: 1, name: /Tokyo, Live/ });
    await user.click((await sidebar()).getByRole("button", { name: /The Weight/ }));
    expect(await screen.findByRole("heading", { level: 1, name: /The Weight/ })).toBeInTheDocument();
  });

  it("navigates tabs by keyboard and focuses search on ⌘K", async () => {
    seedLibrary();
    renderApp();
    const user = userEvent.setup();
    await user.click((await sidebar()).getByRole("button", { name: /Tokyo, Live/ }));
    await screen.findByText("Vocal relationship · density over time");

    await user.keyboard("2");
    expect(await screen.findByText("Chords across time")).toBeInTheDocument();

    await user.keyboard("1");
    expect(await screen.findByText("Vocal relationship · density over time")).toBeInTheDocument();

    await user.keyboard("{Meta>}k{/Meta}");
    expect(screen.getByLabelText("Search library")).toHaveFocus();
  });
});
