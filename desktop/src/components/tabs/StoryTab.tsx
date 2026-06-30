import { TabEmpty } from "./TabEmpty";
import { VOICE_BG, VOICE_LABEL, isVoiceState } from "./voice-taxonomy";
import { cn, formatClock } from "@/lib/utils";
import type { PerceptionDocument } from "@/lib/schemas";

interface StoryTabProps {
  doc: PerceptionDocument;
}

export function StoryTab({ doc }: StoryTabProps) {
  const story = doc.story;
  if (!story || story.story_moments.length === 0) {
    return <TabEmpty>No grounded reading — lyrics weren't available for this track.</TabEmpty>;
  }

  return (
    <div className="mx-auto max-w-2xl space-y-10 px-6 py-8">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold text-fg">{story.title ?? doc.track.title}</h2>
        <p className="font-mono text-xs text-muted">
          {story.total_lines} lines · transcribed via {story.lyrics_source}
        </p>
      </header>

      <ol className="space-y-9">
        {story.story_moments.map((m, i) => {
          const rel = isVoiceState(m.vocal_relationship) ? m.vocal_relationship : null;
          return (
            <li
              key={i}
              style={{ animationDelay: `${Math.min(i * 60, 360)}ms` }}
              className="grid grid-cols-[3.5rem_1fr] gap-4 motion-safe:animate-[step-in_300ms_ease-out_backwards]"
            >
              <div className="pt-1.5 text-right font-mono text-xs text-faint">
                {formatClock(m.time)}
                <div className="mt-1 text-[10px] tracking-wide text-faint/70 uppercase">{m.label}</div>
              </div>

              <div className="space-y-3 border-l border-border pl-4">
                <p className="font-serif text-xl leading-snug text-fg italic">“{m.lyric}”</p>
                <p className="font-serif text-sm text-muted italic">{m.vessel}</p>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11px] text-muted">
                  <span className="text-fg-secondary">{m.chord}</span>
                  <span>{m.emotion}</span>
                  {rel && (
                    <span className="flex items-center gap-1.5">
                      <span className={cn("size-1.5 rounded-full", VOICE_BG[rel])} aria-hidden />
                      {VOICE_LABEL[rel]}
                    </span>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
