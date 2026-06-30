import { createRootRoute, Outlet } from "@tanstack/react-router";
import { Ear } from "lucide-react";

function RootLayout() {
  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-3xl items-center gap-2 px-6 py-4">
          <Ear className="size-5 text-accent" aria-hidden />
          <span className="font-semibold text-fg">Claude's Ears</span>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-6 py-12">
        <Outlet />
      </main>
    </div>
  );
}

function NotFound() {
  return <p className="text-muted">That page isn't here.</p>;
}

function RouteError() {
  return <p className="text-failed">Something went wrong rendering this view.</p>;
}

export const rootRoute = createRootRoute({
  component: RootLayout,
  notFoundComponent: NotFound,
  errorComponent: RouteError,
});
