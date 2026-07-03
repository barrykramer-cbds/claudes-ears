import { useEffect, useRef, useState } from "react";
import { z } from "zod";
import { FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { JobSource } from "@/lib/api";
import { cn } from "@/lib/utils";

type SourceMode = "youtube" | "file";

interface AddTrackModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (source: JobSource) => void;
}

const isHttpUrl = (v: string) => z.url({ protocol: /^https?$/ }).safeParse(v).success;

export function AddTrackModal({ open, onClose, onSubmit }: AddTrackModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [mode, setMode] = useState<SourceMode>("youtube");
  const [url, setUrl] = useState("");
  const [path, setPath] = useState("");
  const [touched, setTouched] = useState(false);
  const hasPicker = typeof window !== "undefined" && Boolean(window.electron);

  // The <dialog> top-layer API is imperative — no store/query/router owns it.
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    else if (!open && dialog.open) dialog.close();
  }, [open]);

  const valid = mode === "youtube" ? isHttpUrl(url.trim()) : path.trim().length > 0;

  const reset = () => {
    setUrl("");
    setPath("");
    setTouched(false);
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!valid) return;
    onSubmit(mode === "youtube" ? { source_url: url.trim() } : { audio_path: path.trim() });
    reset();
  };

  const pick = async () => {
    const picked = await window.electron?.openAudioFile();
    if (picked) setPath(picked);
  };

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
      aria-label="Add a track"
      className={cn(
        "card m-auto w-[26rem] p-0 text-fg backdrop:bg-black/60",
        "scale-100 opacity-100 transition-[opacity,transform] duration-200",
        "[transition-timing-function:var(--ease-out)]",
        "starting:translate-y-1.5 starting:scale-[0.96] starting:opacity-0",
        "motion-reduce:starting:translate-y-0 motion-reduce:starting:scale-100",
      )}
    >
      <form onSubmit={submit} className="space-y-4 p-5">
        <div className="space-y-1">
          <h2 className="text-sm font-semibold tracking-[-0.01em]">Add a track</h2>
          <p className="text-xs text-muted">Analyzed locally — nothing leaves this machine.</p>
        </div>

        <div
          role="group"
          aria-label="Source"
          className="grid grid-cols-2 gap-1 rounded-button border border-border bg-surface-input p-1"
        >
          {(
            [
              ["youtube", "From YouTube"],
              ["file", "From a file"],
            ] as const
          ).map(([m, label]) => (
            <button
              key={m}
              type="button"
              aria-pressed={mode === m}
              onClick={() => {
                setMode(m);
                setTouched(false);
              }}
              className={cn(
                "rounded-[6px] py-1.5 text-xs font-medium transition-colors duration-150 ease-out",
                mode === m ? "bg-surface-hover text-fg" : "text-muted hover:text-fg-secondary",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="min-h-[4.5rem] space-y-1.5">
          {mode === "youtube" ? (
            <>
              <label htmlFor="add-track-url" className="text-xs text-fg-secondary">
                Video URL
              </label>
              <input
                id="add-track-url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onBlur={() => setTouched(true)}
                placeholder="https://www.youtube.com/watch?v=…"
                autoFocus
                spellCheck={false}
                className="w-full rounded-button border border-border bg-surface-input px-3 py-2 font-mono text-xs text-fg outline-none placeholder:text-faint focus-visible:border-accent"
              />
              {touched && !valid && (
                <p className="text-xs text-failed">Paste a full http(s) link to the video.</p>
              )}
            </>
          ) : hasPicker ? (
            <>
              <span className="text-xs text-fg-secondary">Audio file</span>
              <button
                type="button"
                onClick={() => void pick()}
                className="flex w-full items-center gap-2 rounded-button border border-dashed border-border-strong px-3 py-2 text-left text-xs text-muted transition-colors duration-150 hover:border-faint hover:text-fg"
              >
                <FolderOpen className="size-3.5 shrink-0" aria-hidden />
                <span className="truncate font-mono">{path || "Choose a file…"}</span>
              </button>
              {touched && !valid && <p className="text-xs text-failed">Choose an audio file.</p>}
            </>
          ) : (
            <>
              <label htmlFor="add-track-path" className="text-xs text-fg-secondary">
                Local file path
              </label>
              <input
                id="add-track-path"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                onBlur={() => setTouched(true)}
                placeholder="/music/song.flac"
                autoFocus
                spellCheck={false}
                className="w-full rounded-button border border-border bg-surface-input px-3 py-2 font-mono text-xs text-fg outline-none placeholder:text-faint focus-visible:border-accent"
              />
              {touched && !valid && (
                <p className="text-xs text-failed">Enter a path the analyzer can read.</p>
              )}
            </>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={touched && !valid}>
            Analyze
          </Button>
        </div>
      </form>
    </dialog>
  );
}
