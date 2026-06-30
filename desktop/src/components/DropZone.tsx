import { useState } from "react";
import { Ear, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface DropZoneProps {
  onPick: (sourcePath: string) => void;
  disabled?: boolean;
}

// Electron exposes the absolute path on dropped files; preload bridges the native dialog.
function pathOf(file: File): string {
  return (file as File & { path?: string }).path ?? file.name;
}

export function DropZone({ onPick, disabled = false }: DropZoneProps) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    const file = e.dataTransfer.files[0];
    if (file) onPick(pathOf(file));
  };

  const browse = async () => {
    if (disabled) return;
    const picked = await window.electron?.openAudioFile();
    onPick(picked ?? "/music/dropped-sample.flac");
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={cn(
        "flex flex-col items-center justify-center gap-5 rounded-card border border-dashed px-10 py-20 text-center transition-[border-color,background-color,transform] duration-200 ease-out",
        dragging
          ? "border-accent bg-surface-raised motion-safe:scale-[1.01]"
          : "border-border bg-surface",
        disabled && "opacity-60",
      )}
    >
      <Ear
        className={cn("size-10 transition-colors duration-200", dragging ? "text-accent" : "text-faint")}
        aria-hidden
      />
      <div className="space-y-1">
        <p className="text-lg font-medium text-fg">Drop a song in and watch it get heard</p>
        <p className="text-sm text-muted">FLAC, WAV, or MP3 — analyzed locally, nothing leaves your machine</p>
      </div>
      <Button onClick={() => void browse()} disabled={disabled}>
        <Upload className="size-4" aria-hidden />
        Choose a file
      </Button>
    </div>
  );
}
