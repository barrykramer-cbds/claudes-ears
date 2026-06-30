// Mirrors the orchestrated order of src/claudes_ears/pipeline/steps.py
// (ORCHESTRATED_STEP_COUNT === 21). `name` is the SSE step id; `label` is for display.
export interface PipelineStep {
  name: string;
  label: string;
  phase: string;
}

export const PIPELINE_STEPS: readonly PipelineStep[] = [
  { name: "separation", label: "Separating stems", phase: "Separation" },
  { name: "analyze_stems", label: "Analyzing stems", phase: "Stems" },
  { name: "freq_interaction", label: "Frequency interaction", phase: "Stems" },
  { name: "groove_timing", label: "Groove & timing", phase: "Stems" },
  { name: "timbral_decomposition", label: "Timbral decomposition", phase: "Stems" },
  { name: "vocal_layers", label: "Vocal layers", phase: "Vocals" },
  { name: "vocal_intervals", label: "Vocal intervals", phase: "Vocals" },
  { name: "vocal_narrative", label: "Vocal narrative", phase: "Vocals" },
  { name: "vocal_relationships", label: "Vocal relationships", phase: "Vocals" },
  { name: "register_tracking", label: "Register tracking", phase: "Vocals" },
  { name: "breath_detection", label: "Breath detection", phase: "Vocals" },
  { name: "stereo_field", label: "Stereo field", phase: "Full mix" },
  { name: "temporal_segmentation", label: "Temporal segmentation", phase: "Full mix" },
  { name: "depth_reverb", label: "Depth & reverb", phase: "Full mix" },
  { name: "chord_progression", label: "Chord progression", phase: "Full mix" },
  { name: "harmonic_rhythm", label: "Harmonic rhythm", phase: "Derived" },
  { name: "music_theory", label: "Music theory", phase: "Derived" },
  { name: "emotional_trajectory", label: "Emotional trajectory", phase: "Derived" },
  { name: "semantic_lyrics", label: "Semantic lyrics", phase: "Derived" },
  { name: "story_reader", label: "Story reading", phase: "Derived" },
  { name: "ai_detector", label: "AI detection", phase: "Derived" },
] as const;

export const PIPELINE_STEP_COUNT = PIPELINE_STEPS.length;
