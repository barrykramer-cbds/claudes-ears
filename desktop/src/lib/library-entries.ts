import { isVoiceState, type VoiceState } from "@/components/tabs/voice-taxonomy";
import type { PerceptionDocument, TrackSummary } from "@/lib/schemas";

// One row of the library, whichever side it came from: the DuckDB index
// (`GET /library`) or a PerceptionDocument analyzed this session.
export interface LibraryEntry {
  id: string;
  title: string;
  artist: string | null;
  keyMode: string | null;
  tempo: number | null;
  durationS: number | null;
  verdict: string | null;
  era: string | null;
  analyzedAt: string | null;
  voice: VoiceState | null;
  hasDoc: boolean;
}

export function dominantVoice(doc: PerceptionDocument): VoiceState | null {
  const dist = doc.vocals?.relationships?.relationship_distribution;
  if (!dist) return null;
  const top = Object.entries(dist).sort((a, b) => b[1] - a[1])[0]?.[0];
  return top && isVoiceState(top) ? top : null;
}

export function entryFromDoc(doc: PerceptionDocument): LibraryEntry {
  const theory = doc.harmony?.theory;
  return {
    id: doc.track.id,
    title: doc.track.title ?? doc.track.id,
    artist: doc.track.artist ?? null,
    keyMode: theory ? `${theory.key} ${theory.mode}` : null,
    tempo: doc.rhythm?.groove?.tempo ?? doc.stems?.drums?.tempo_bpm ?? null,
    durationS: doc.track.duration_s ?? null,
    verdict: doc.ai_detection?.verdict ?? null,
    era: doc.track.era ?? doc.track.genre ?? null,
    analyzedAt: doc.track.analyzed_at,
    voice: dominantVoice(doc),
    hasDoc: true,
  };
}

export function entryFromSummary(s: TrackSummary): LibraryEntry {
  return {
    id: s.track_id,
    title: s.title ?? s.track_id,
    artist: s.artist ?? null,
    keyMode: s.key ? `${s.key} ${s.mode ?? ""}`.trim() : null,
    tempo: s.tempo ?? null,
    durationS: s.duration_s ?? null,
    verdict: s.ai_verdict ?? null,
    era: s.era ?? s.genre ?? null,
    analyzedAt: s.analyzed_at ?? null,
    voice: null,
    hasDoc: false,
  };
}

// Documents win over summaries for the same id (they carry the voice + full lenses).
export function mergeEntries(
  summaries: readonly TrackSummary[],
  docs: readonly PerceptionDocument[],
): LibraryEntry[] {
  const byId = new Map<string, LibraryEntry>();
  for (const s of summaries) byId.set(s.track_id, entryFromSummary(s));
  for (const d of docs) byId.set(d.track.id, entryFromDoc(d));
  return [...byId.values()].sort((a, b) =>
    (b.analyzedAt ?? "").localeCompare(a.analyzedAt ?? ""),
  );
}
