import { useEffect } from "react";
import { TAB_IDS, TABS, type TabId } from "@/lib/tabs";
import type { PerceptionDocument } from "@/lib/schemas";
import { TrackHeader } from "./TrackHeader";
import { TimeScrubber } from "./TimeScrubber";
import { TabBar } from "./TabBar";
import { VoicesTab } from "@/components/tabs/VoicesTab";
import { HarmonyTab } from "@/components/tabs/HarmonyTab";
import { StructureTab } from "@/components/tabs/StructureTab";
import { SpaceTab } from "@/components/tabs/SpaceTab";
import { AiLensTab } from "@/components/tabs/AiLensTab";
import { StoryTab } from "@/components/tabs/StoryTab";
import { LibraryTab } from "@/components/tabs/LibraryTab";

interface WorkspaceProps {
  doc: PerceptionDocument;
  tab: TabId;
  onTabChange: (id: TabId) => void;
}

export function Workspace({ doc, tab, onTabChange }: WorkspaceProps) {
  // Global tab keys (←/→, 1–7) — window events have no Query/store/router owner.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || e.target instanceof HTMLInputElement) return;
      const idx = TAB_IDS.indexOf(tab);
      if (e.key === "ArrowRight") onTabChange(TAB_IDS[Math.min(idx + 1, TAB_IDS.length - 1)]!);
      else if (e.key === "ArrowLeft") onTabChange(TAB_IDS[Math.max(idx - 1, 0)]!);
      else if (/^[1-7]$/.test(e.key)) onTabChange(TAB_IDS[Number(e.key) - 1]!);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tab, onTabChange]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <TrackHeader doc={doc} />
      <TimeScrubber durationS={doc.track.duration_s ?? 0} />
      <TabBar tabs={TABS} active={tab} onSelect={onTabChange} />
      <div role="tabpanel" className="min-h-0 flex-1 overflow-auto">
        <TabContent doc={doc} tab={tab} />
      </div>
    </div>
  );
}

function TabContent({ doc, tab }: { doc: PerceptionDocument; tab: TabId }) {
  switch (tab) {
    case "voices":
      return <VoicesTab doc={doc} />;
    case "harmony":
      return <HarmonyTab doc={doc} />;
    case "structure":
      return <StructureTab doc={doc} />;
    case "space":
      return <SpaceTab doc={doc} />;
    case "ai":
      return <AiLensTab doc={doc} />;
    case "story":
      return <StoryTab doc={doc} />;
    case "library":
      return <LibraryTab doc={doc} />;
  }
}
