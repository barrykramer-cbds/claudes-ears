import { Badge } from "@/components/ui/badge";
import { Eyebrow } from "@/components/ui/eyebrow";
import { TabEmpty } from "./TabEmpty";
import type { PerceptionDocument } from "@/lib/schemas";

interface AiLensTabProps {
  doc: PerceptionDocument;
}

const clamp01 = (n: number) => Math.min(1, Math.max(0, n));

function title(key: string): string {
  return key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export function AiLensTab({ doc }: AiLensTabProps) {
  const ai = doc.ai_detection;
  if (!ai) return <TabEmpty>This track wasn't run through the AI lens.</TabEmpty>;

  const isHuman = ai.verdict === "human";
  const rows = Object.entries(ai.vectors).filter(
    ([, v]) => v.value != null && v.human_avg != null && v.ai_avg != null,
  );

  return (
    <div className="mx-auto max-w-3xl space-y-5 p-6 motion-safe:animate-[step-in_240ms_ease-out]">
      <section className="card p-6">
        <Eyebrow>The lens</Eyebrow>
        <p className="mt-3 max-w-xl font-serif text-lg leading-snug text-fg italic">
          {isHuman ? "The voice argues with itself." : "The voice agrees with itself."}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Badge dotClassName={isHuman ? "bg-done" : "bg-failed"}>
            reads {ai.verdict} · {ai.overall_score.toFixed(2)}
          </Badge>
          <Badge>{ai.confidence} confidence</Badge>
          <Badge>
            {ai.vectors_available}/{ai.vectors_possible} signals
          </Badge>
        </div>

        <div className="mt-5">
          <div className="flex justify-between font-mono text-[10px] tracking-[0.12em] uppercase">
            <span className="text-done">human · argues</span>
            <span className="text-failed">agrees · AI</span>
          </div>
          <div className="relative mt-2 h-1.5 rounded-pill bg-gradient-to-r from-done/60 to-failed/60">
            <div
              className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-bg bg-fg"
              style={{ left: `${clamp01(ai.overall_score) * 100}%` }}
            />
          </div>
        </div>
      </section>

      <section className="card p-6">
        <Eyebrow>Signal by signal</Eyebrow>
        <ul className="mt-5 space-y-6">
          {rows.length === 0 && <li className="text-sm text-muted">No per-signal reads available.</li>}
          {rows.map(([key, v]) => {
            const value = v.value!;
            const leansHuman = Math.abs(value - v.human_avg!) <= Math.abs(value - v.ai_avg!);
            return (
              <li key={key}>
                <div className="flex items-baseline justify-between">
                  <span className="text-sm font-medium text-fg">{title(key)}</span>
                  <span className="font-mono text-xs text-muted">
                    leans {leansHuman ? "human" : "AI"}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-muted">{v.signal}</p>
                <div className="relative mt-3 h-px bg-border">
                  <Tick at={v.ai_avg!} className="bg-failed" label="AI" />
                  <Tick at={v.human_avg!} className="bg-done" label="human" />
                  <div
                    className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-fg shadow-[0_0_8px_-1px_var(--color-fg)]"
                    style={{ left: `${clamp01(value) * 100}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}

function Tick({ at, className, label }: { at: number; className: string; label: string }) {
  return (
    <div className="absolute top-1/2 -translate-y-1/2" style={{ left: `${clamp01(at) * 100}%` }}>
      <div className={`h-3 w-px -translate-x-1/2 ${className}`} />
      <span className="absolute top-2.5 left-0 -translate-x-1/2 font-mono text-[9px] text-faint">
        {label}
      </span>
    </div>
  );
}
