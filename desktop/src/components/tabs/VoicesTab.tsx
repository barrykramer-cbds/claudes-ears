import { Badge } from "@/components/ui/badge";
import type { PerceptionDocument } from "@/lib/schemas";
import { Beeswarm } from "./Beeswarm";
import { DistributionBars } from "./DistributionBars";
import { RegisterReadout } from "./RegisterReadout";
import { VOICE_BG, VOICE_LABEL, isVoiceState } from "./voice-taxonomy";

interface VoicesTabProps {
  doc: PerceptionDocument;
}

export function VoicesTab({ doc }: VoicesTabProps) {
  const rel = doc.vocals?.relationships;
  const ai = doc.ai_detection;

  if (!rel) {
    return (
      <p className="px-6 py-20 text-center text-sm text-muted">
        No vocal-relationship reading for this track.
      </p>
    );
  }

  const dominant = Object.entries(rel.relationship_distribution).sort((a, b) => b[1] - a[1])[0]?.[0];
  const reading = rel.story
    .map((s) => s.narrative)
    .filter(Boolean)
    .join(" — ");

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6 motion-safe:animate-[step-in_240ms_ease-out]">
      <Beeswarm distribution={rel.relationship_distribution} durationS={rel.duration} />

      <div className="grid gap-4 md:grid-cols-[1.15fr_1fr]">
        <DistributionBars distribution={rel.relationship_distribution} />
        <RegisterReadout doc={doc} />
      </div>

      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {dominant && isVoiceState(dominant) && (
            <Badge dotClassName={VOICE_BG[dominant]}>{VOICE_LABEL[dominant]} dominant</Badge>
          )}
          {ai && (
            <Badge dotClassName={ai.verdict === "human" ? "bg-done" : "bg-failed"}>
              {ai.verdict} · {ai.overall_score.toFixed(2)}
            </Badge>
          )}
        </div>
        {reading && (
          <p className="max-w-2xl font-serif text-[15px] leading-relaxed text-fg-secondary italic">
            “{reading}”
          </p>
        )}
      </div>
    </div>
  );
}
