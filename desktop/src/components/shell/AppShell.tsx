import { useState } from "react";
import { Titlebar } from "./Titlebar";
import { LibrarySidebar } from "./LibrarySidebar";
import { cn } from "@/lib/utils";

interface AppShellProps {
  selectedId: string | null;
  onSelectTrack: (id: string) => void;
  onAdd: () => void;
  children: React.ReactNode;
}

export function AppShell({ selectedId, onSelectTrack, onAdd, children }: AppShellProps) {
  const [query, setQuery] = useState("");
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="grid h-screen grid-rows-[44px_1fr] bg-bg">
      <Titlebar query={query} onQuery={setQuery} onAdd={onAdd} />
      <div
        className={cn(
          "grid min-h-0",
          collapsed ? "grid-cols-[44px_1fr]" : "grid-cols-[232px_1fr]",
        )}
      >
        <LibrarySidebar
          selectedId={selectedId}
          onSelect={onSelectTrack}
          onAdd={onAdd}
          query={query}
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed((c) => !c)}
        />
        <main className="flex min-h-0 flex-col overflow-hidden">{children}</main>
      </div>
    </div>
  );
}
