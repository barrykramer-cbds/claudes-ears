import { Eyebrow } from "@/components/ui/eyebrow";
import type { PerceptionDocument } from "@/lib/schemas";
import { StatGrid, type Stat } from "./StatGrid";

interface RegisterReadoutProps {
  doc: PerceptionDocument;
}

function fmt(n: number | null | undefined, digits = 1): string | null {
  return typeof n === "number" ? n.toFixed(digits) : null;
}

export function RegisterReadout({ doc }: RegisterReadoutProps) {
  const vox = doc.stems?.vocals;
  const register = doc.vocals?.register;

  const pitch = fmt(register?.singer_median_f0 ?? vox?.pitch_mean_hz);
  const range = fmt(vox?.pitch_range_semitones);
  const breathiness = fmt(vox?.breathiness, 2);
  const voiced = fmt(vox?.voiced_fraction, 2);

  const stats: Stat[] = [
    { label: "pitch", value: pitch ?? "—", unit: pitch ? "Hz" : undefined },
    { label: "breath", value: breathiness ?? "—" },
    { label: "range", value: range ?? "—", unit: range ? "st" : undefined },
    { label: "voiced", value: voiced ?? "—" },
  ];

  return (
    <section className="card p-5">
      <Eyebrow>Register · breath</Eyebrow>
      <StatGrid stats={stats} className="mt-4 grid-cols-2" />
    </section>
  );
}
