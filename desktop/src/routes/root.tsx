import { createRootRoute, Outlet } from "@tanstack/react-router";

function RootLayout() {
  return (
    <div className="min-h-screen bg-bg text-fg">
      <Outlet />
    </div>
  );
}

function NotFound() {
  return <p className="p-6 text-muted">That page isn't here.</p>;
}

function RouteError() {
  return <p className="p-6 text-failed">Something went wrong rendering this view.</p>;
}

export const rootRoute = createRootRoute({
  component: RootLayout,
  notFoundComponent: NotFound,
  errorComponent: RouteError,
});
