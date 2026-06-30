import { z } from "zod";

export const TAB_IDS = [
  "voices",
  "harmony",
  "structure",
  "space",
  "ai",
  "story",
  "library",
] as const;

export type TabId = (typeof TAB_IDS)[number];
export const TabIdSchema = z.enum(TAB_IDS);

export interface TabDef {
  id: TabId;
  label: string;
}

export const TABS: readonly TabDef[] = [
  { id: "voices", label: "Voices" },
  { id: "harmony", label: "Harmony" },
  { id: "structure", label: "Structure" },
  { id: "space", label: "Space" },
  { id: "ai", label: "AI lens" },
  { id: "story", label: "Story" },
  { id: "library", label: "Library" },
];
