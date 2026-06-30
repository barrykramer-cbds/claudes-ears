import { Button } from "@/components/ui/button";
import type { PerceptionDocument } from "@/lib/schemas";

interface PerceptionSummaryProps {
  doc: PerceptionDocument;
  onReset: () => void;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <p className="text-xs tracking-wide text-faint uppercase">{label}</p>
      <p className="text-lg font-medium text-fg">{value}</p>
    </div>
  );
}

export function PerceptionSummary({ doc, onReset }: PerceptionSummaryProps) {
  const { track, harmony, rhythm, ai_detection, emotion, story } = doc;
  const key = harmony?.theory ? `${harmony.theory.key} ${harmony.theory.mode}` : "—";
  const tempo = rhythm?.groove ? `${Math.round(rhythm.groove.tempo)} BPM` : "—";
  const voice = ai_detection ? `${ai_detection.verdict} (${ai_detection.confidence})` : "—";

  return (
    <article className="space-y-8 motion-safe:animate-[step-in_240ms_ease-out]">
      <header className="space-y-1">
        <h2 className="text-2xl font-semibold text-fg">{track.title ?? track.id}</h2>
        {track.artist && <p className="text-muted">{track.artist}</p>}
      </header>

      <div className="grid grid-cols-3 gap-6 rounded-card bg-surface p-6">
        <Stat label="Key" value={key} />
        <Stat label="Tempo" value={tempo} />
        <Stat label="Voice" value={voice} />
      </div>

      {emotion?.narrative && (
        <div className="space-y-1">
          <p className="text-xs tracking-wide text-faint uppercase">Emotional arc</p>
          <p className="text-fg">{emotion.narrative}</p>
        </div>
      )}

      {story?.story_moments[0] && (
        <blockquote className="border-l-2 border-accent pl-4 text-muted italic">
          “{story.story_moments[0].lyric}” — {story.story_moments[0].vessel}
        </blockquote>
      )}

      <Button variant="ghost" size="sm" onClick={onReset}>
        Listen to another
      </Button>
    </article>
  );
}
