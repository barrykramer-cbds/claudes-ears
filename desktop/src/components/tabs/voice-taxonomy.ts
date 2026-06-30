export const VOICE_STATES = [
  "solo",
  "support",
  "dialogue",
  "opposition",
  "merge",
  "withdraw",
] as const;

export type VoiceState = (typeof VOICE_STATES)[number];

export const VOICE_LABEL: Record<VoiceState, string> = {
  solo: "Solo",
  support: "Support",
  dialogue: "Dialogue",
  opposition: "Opposition",
  merge: "Merge",
  withdraw: "Withdraw",
};

export const VOICE_TEXT: Record<VoiceState, string> = {
  solo: "text-solo",
  support: "text-support",
  dialogue: "text-dialogue",
  opposition: "text-opposition",
  merge: "text-merge",
  withdraw: "text-withdraw",
};

export const VOICE_BG: Record<VoiceState, string> = {
  solo: "bg-solo",
  support: "bg-support",
  dialogue: "bg-dialogue",
  opposition: "bg-opposition",
  merge: "bg-merge",
  withdraw: "bg-withdraw",
};

export function isVoiceState(value: string): value is VoiceState {
  return (VOICE_STATES as readonly string[]).includes(value);
}
