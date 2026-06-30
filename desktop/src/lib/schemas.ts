import { z } from "zod";

// Zod mirror of src/claudes_ears/models/{perception,jobs}.py — the boundary contract.
// `| None = None` Pydantic fields map to `.nullish()`; aliased keys use the JSON key
// (`from`/`register`/`class`); default-factory collections default to empty.

const num = z.number();
const str = z.string();
const strNumMap = z.record(z.string(), z.number()).default({});

// --- jobs.py -----------------------------------------------------------------
export const JobStatusSchema = z.enum(["queued", "running", "completed", "failed"]);
export const StepStatusSchema = z.enum(["started", "completed", "failed", "skipped"]);

export const ProgressEventSchema = z.object({
  job_id: str,
  step: str,
  index: z.number().int().min(1),
  total: z.number().int().min(1),
  status: StepStatusSchema,
  message: str.nullish(),
});

export const JobSchema = z.object({
  id: str,
  source_path: str,
  status: JobStatusSchema,
  current_step: str.nullish(),
  step_index: z.number().int(),
  step_total: z.number().int(),
  error: str.nullish(),
  created_at: str,
  finished_at: str.nullish(),
});

// --- perception.py: track + separation ---------------------------------------
const TrackMeta = z.object({
  id: str,
  source_path: str,
  analyzed_at: str,
  pipeline_version: str,
  title: str.nullish(),
  artist: str.nullish(),
  duration_s: num.nullish(),
  sample_rate: num.nullish(),
  year: num.nullish(),
  genre: str.nullish(),
  era: str.nullish(),
});

const SeparationInfo = z.object({
  stems_present: z.array(str).default([]),
  stem_dir: str,
  model: str.nullish(),
});

// --- stems -------------------------------------------------------------------
const KitBalance = z.object({ kick: num, snare: num, hihat: num });

const VocalsStem = z.object({
  duration: num,
  breathiness: num,
  breathiness_desc: str,
  dynamic_range_db: num,
  stem: str.nullish(),
  pitch_mean_hz: num.nullish(),
  pitch_range_semitones: num.nullish(),
  voiced_fraction: num.nullish(),
  vocal_melodic_entropy: num.nullish(),
});

const DrumsStem = z.object({
  duration: num,
  tempo_bpm: num,
  onsets_per_second: num,
  kit_balance: KitBalance,
  stem: str.nullish(),
  beat_regularity: num.nullish(),
});

const BassStem = z.object({
  duration: num,
  dominant_notes: z.array(str).default([]),
  root_movement_rate: num,
  root_movement_desc: str,
  stem: str.nullish(),
});

const OtherStem = z.object({
  duration: num,
  centroid_hz: num,
  bandwidth_hz: num,
  texture: str,
  harmonic_pct: num,
  attack: str,
  stem: str.nullish(),
});

const StemAnalysis = z.object({
  vocals: VocalsStem.nullish(),
  drums: DrumsStem.nullish(),
  bass: BassStem.nullish(),
  other: OtherStem.nullish(),
});

// --- vocals ------------------------------------------------------------------
const Echo = z.object({ delay_s: num, strength: num });
const DenseRegion = z.object({ start: num, end: num, density: num });

const VocalLayers = z.object({
  duration: num,
  layering: str,
  echo_detected: z.boolean(),
  harmonic_peaks_mean: num.nullish(),
  harmonic_peaks_p90: num.nullish(),
  echo_count: num.nullish(),
  echoes: z.array(Echo).nullish(),
  echo_desc: str.nullish(),
  dense_regions: z.array(DenseRegion).nullish(),
  layering_pct: num.nullish(),
});

const IntervalProfileEntry = z.object({
  semitones: num,
  name: str,
  meaning: str,
  count: num,
  pct: num,
});
const SampleInterval = z.object({ time: num, interval: num, semitones_raw: num });
const DominantInterval = z.object({ name: str, meaning: str, pct: num });

const VocalIntervals = z.object({
  duration: num,
  total_interval_events: num,
  consonance_ratio: num,
  harmonic_character: str,
  interval_profile: z.array(IntervalProfileEntry).default([]),
  sample_intervals: z.array(SampleInterval).default([]),
  dominant_interval: DominantInterval.nullish(),
});

const NarrativeSegment = z.object({
  time: num,
  label: str,
  type: str,
  energy_db: num,
  peak_count: num,
  pitch_spread: num,
  spectral_width: num,
  solo_score: num,
  chorus_score: num,
  peak_max: num.nullish(),
  pitch_mean: num.nullish(),
  harmonic_ratio: num.nullish(),
});
const NarrativePhase = z.object({
  type: str,
  start: str,
  start_time: num,
  end: str,
  end_time: num,
  duration_s: num,
  avg_energy: num,
  avg_peaks: num,
});
const CallResponse = z.object({
  call_time: str,
  call_type: str,
  response_time: str,
  response_type: str,
  pattern: str,
});
const VocalNarrative = z.object({
  duration: num,
  total_phases: num,
  total_call_response: num,
  type_distribution: strNumMap,
  phases: z.array(NarrativePhase).default([]),
  call_response_patterns: z.array(CallResponse).default([]),
  segments: z.array(NarrativeSegment).default([]),
});

const RelationshipMoment = z.object({
  time: num,
  label: str,
  relationship: str,
  energy_db: num,
  density: num,
  density_change: num,
  lead_present: z.boolean(),
  support_register: str,
  narrative: str,
  lead_pct: num.nullish(),
  below_pct: num.nullish(),
  above_pct: num.nullish(),
});
const RelationshipStory = z.object({
  relationship: str,
  narrative: str,
  start: str,
  start_time: num,
  end: str,
  duration_s: num,
  avg_density: num,
});
const RelationshipTransition = z.object({
  time: str,
  from: str,
  to: str,
  from_narrative: str,
  to_narrative: str,
});
const VocalRelationships = z.object({
  duration: num,
  lead_pitch_center: num,
  total_story_phases: num,
  total_transitions: num,
  relationship_distribution: strNumMap,
  story: z.array(RelationshipStory).default([]),
  transitions: z.array(RelationshipTransition).default([]),
  moments: z.array(RelationshipMoment).default([]),
});

const RegisterMoment = z.object({
  time: num,
  label: str,
  register: str,
  confidence: num,
  f0: num,
  energy_db: num,
  spectral_slope: num.nullish(),
  harmonic_ratio: num.nullish(),
});
const RegisterPhase = z.object({
  register: str,
  start: str,
  start_time: num,
  end: str,
  end_time: num,
  duration_s: num,
  avg_f0: num.nullish(),
});
const RegisterTransition = z.object({
  time: str,
  from_register: str,
  to_register: str,
  from_f0: num,
  to_f0: num,
  direction: str,
  drama: str,
});
const RegisterTracking = z.object({
  duration: num,
  singer_median_f0: num,
  singer_range_low: num,
  singer_range_high: num,
  total_register_phases: num,
  total_transitions: num,
  register_distribution: strNumMap,
  phases: z.array(RegisterPhase).default([]),
  transitions: z.array(RegisterTransition).default([]),
  moments: z.array(RegisterMoment).default([]),
});

const BreathEvent = z.object({
  time: num,
  end: num,
  duration_s: num,
  label: str,
  depth: str,
  avg_flatness: num,
  avg_energy_db: num,
  avg_centroid: num,
  context: str,
});
const DepthDistribution = z.object({ deep: num, normal: num, catch: num });
const BreathDetection = z.object({
  duration: num,
  total_breaths: num,
  breaths_per_minute: num,
  avg_breath_duration_s: num,
  avg_inter_breath_interval_s: num,
  avg_phrase_duration_s: num,
  longest_phrase_s: num,
  depth_distribution: DepthDistribution,
  context_distribution: z.record(z.string(), z.number()).default({}),
  breath_events: z.array(BreathEvent).default([]),
  phrase_durations: z.array(num).default([]),
  min_inter_breath_interval_s: num.nullish(),
  max_inter_breath_interval_s: num.nullish(),
});

const VocalAnalysis = z.object({
  layers: VocalLayers.nullish(),
  intervals: VocalIntervals.nullish(),
  narrative: VocalNarrative.nullish(),
  relationships: VocalRelationships.nullish(),
  register: RegisterTracking.nullish(),
  breath: BreathDetection.nullish(),
});

// --- rhythm ------------------------------------------------------------------
const TimingDistribution = z.object({ behind_pct: num, on_grid_pct: num, ahead_pct: num });
const GrooveTiming = z.object({
  duration: num,
  tempo: num,
  beat_count: num,
  mean_deviation_ms: num.nullish(),
  std_deviation_ms: num.nullish(),
  median_deviation_ms: num.nullish(),
  feel: str.nullish(),
  tightness: str.nullish(),
  swing_ratio: num.nullish(),
  swing_character: str.nullish(),
  drift_quarters_ms: z.array(num).nullish(),
  drift: str.nullish(),
  timing_distribution: TimingDistribution.nullish(),
  error: str.nullish(),
});
const RhythmAnalysis = z.object({ groove: GrooveTiming.nullish() });

// --- harmony -----------------------------------------------------------------
const ChordSegment = z.object({
  chord: str,
  start: num,
  start_beat: num,
  end: num,
  end_beat: num,
  duration_beats: num,
  avg_confidence: num,
});
const ChordPattern = z.object({ pattern: str, count: num });
const Modulation = z.object({ time: num, from: str, to: str });
const ChordProgression = z.object({
  tempo: num,
  total_beats: num,
  total_segments: num,
  unique_chords: num,
  segments: z.array(ChordSegment).default([]),
  top_patterns: z.array(ChordPattern).default([]),
  modulations: z.array(Modulation).default([]),
  chord_sequence_summary: z.array(str).default([]),
});

const HarmonicWindow = z.object({
  time: num,
  label: str,
  changes: num,
  changes_per_beat: num,
  changes_per_bar: num,
  avg_interval_s: num,
  rhythm_class: str,
  narrative: str,
});
const HarmonicPhase = z.object({
  class: str,
  start: str,
  start_time: num,
  end: str,
  end_time: num,
  duration_s: num,
  avg_changes_per_bar: num,
  narrative: str,
});
const AccelerationEvent = z.object({
  time: str,
  type: str,
  from_rate: num,
  to_rate: num,
  magnitude: num,
  narrative: str,
});
const HarmonicRhythm = z.object({
  total_changes: num,
  windows: z.array(HarmonicWindow).default([]),
  total_chord_events: num.nullish(),
  tempo_bpm: num.nullish(),
  duration: num.nullish(),
  avg_changes_per_bar: num.nullish(),
  max_changes_per_bar: num.nullish(),
  min_changes_per_bar: num.nullish(),
  harmonic_arc: str.nullish(),
  total_phases: num.nullish(),
  total_accel_events: num.nullish(),
  phases: z.array(HarmonicPhase).nullish(),
  acceleration_events: z.array(AccelerationEvent).nullish(),
});

const ChordAnalysis = z.object({
  numeral: str,
  function: str,
  tension: num,
  color: str,
  is_chromatic: z.boolean(),
});
const AnalyzedChord = z.object({
  chord: str,
  start: num,
  end: num,
  label: str,
  analysis: ChordAnalysis.nullish(),
});
const Cadence = z.object({
  type: str,
  strength: str,
  narrative: str,
  time: num,
  label: str,
  from: str,
  to: str,
});
const MusicTheory = z.object({
  key: str,
  mode: str,
  key_confidence: num.nullish(),
  total_chords: num,
  unique_numerals: z.array(str).default([]),
  harmonic_vocabulary_size: num,
  chromatic_chords_pct: num,
  total_cadences: num,
  cadence_distribution: z.record(z.string(), z.number()).default({}),
  cadences: z.array(Cadence).default([]),
  analyzed_chords: z.array(AnalyzedChord).default([]),
});

const HarmonyAnalysis = z.object({
  chords: ChordProgression.nullish(),
  harmonic_rhythm: HarmonicRhythm.nullish(),
  theory: MusicTheory.nullish(),
});

// --- timbre ------------------------------------------------------------------
const TopFrequency = z.object({ hz: num, weight: num });
const ActivationPoint = z.object({ time: num, level: num });
const TimbralComponent = z.object({
  component: num,
  centroid_hz: num,
  bandwidth_hz: num,
  harmonic_pct: num,
  attack_sharpness: num,
  attack_type: str,
  active_pct: num,
  energy_contribution: num,
  peak_time: num,
  peak_time_label: str,
  instrument_guess: str,
  classification_confidence: num,
  energy_pct: num,
  rank: num,
  top_frequencies: z.array(TopFrequency).default([]),
  activation_envelope: z.array(ActivationPoint).default([]),
});
const TimbralDecomposition = z.object({
  duration: num,
  n_components: num,
  reconstruction_error: num,
  components: z.array(TimbralComponent).default([]),
});
const PairBand = z.object({ overlap: num, correlation: num, dominance: num, dominant: str });
const FreqPair = z.object({
  pair: str,
  bands: z.record(z.string(), PairBand).default({}),
  overall_overlap: num,
  competition: str,
});
const FreqInteraction = z.object({
  stem_count: num,
  pairs: z.array(FreqPair).default([]),
  territory: z.record(z.string(), z.record(z.string(), z.number())).default({}),
});
const TimbreAnalysis = z.object({
  decomposition: TimbralDecomposition.nullish(),
  interaction: FreqInteraction.nullish(),
});

// --- spatial -----------------------------------------------------------------
const WidthTimelinePoint = z.object({ time: num, width: num, balance: num });
const StereoEvent = z.object({ time: num, type: str, magnitude: num });
const StereoField = z.object({
  stereo: z.boolean(),
  note: str.nullish(),
  duration: num.nullish(),
  mid_pct: num.nullish(),
  side_pct: num.nullish(),
  stereo_width: num.nullish(),
  width_desc: str.nullish(),
  lr_balance: num.nullish(),
  balance_desc: str.nullish(),
  lr_correlation: num.nullish(),
  correlation_desc: str.nullish(),
  band_width: z.record(z.string(), z.number()).nullish(),
  widest_band: str.nullish(),
  narrowest_band: str.nullish(),
  width_timeline: z.array(WidthTimelinePoint).nullish(),
  stereo_events: z.array(StereoEvent).nullish(),
});
const DepthReverb = z.object({
  duration: num,
  rt60_estimate: num,
  pre_delay_ms: num,
  spectral_persistence: num,
  spectral_flatness_mean: num,
  spectral_flatness_std: num,
  wetness_index: num,
  room_size: str,
  perceived_distance: str,
  spatial_placement: str,
  rt60_std: num.nullish(),
});
const SpatialAnalysis = z.object({
  stereo: StereoField.nullish(),
  depth: DepthReverb.nullish(),
});

// --- structure ---------------------------------------------------------------
const Snapshot = z.object({
  seg: num,
  t_start: num,
  t_end: num,
  t_center: num,
  time: str,
  rms_mean: num,
  rms_p90: num,
  dyn_range: num,
  centroid: num,
  harm_pct: num,
  key: str,
  tension: num,
  consonance: num,
  warmth: num,
  onset_density: num,
  tempo: num,
});
const PointDb = z.object({ time: str, db: num });
const PointVal = z.object({ time: str, val: num });
const StructureTransition = z.object({ time: str, type: str, db: num });
const KeyChange = z.object({ time: str, from: str, to: str });
const Arc = z.object({
  energy: str,
  e_thirds: z.array(num.nullable()).default([]),
  t_thirds: z.array(num.nullable()).default([]),
});
const StructureNarrative = z.object({
  climax: PointDb.nullish(),
  quietest: PointDb.nullish(),
  peak_tension: PointVal.nullish(),
  transitions: z.array(StructureTransition).default([]),
  key_changes: z.array(KeyChange).default([]),
  arc: Arc.nullish(),
});
const StructureAnalysis = z.object({
  snapshots: z.array(Snapshot).default([]),
  narrative: StructureNarrative.nullish(),
});

// --- emotion -----------------------------------------------------------------
const TrajectorySummaryPoint = z.object({ time: str, state: str, energy: str });
const EmotionPhase = z.object({
  state: str,
  energy: str,
  start: str,
  end: str,
  duration_s: num,
  avg_tension: num,
  avg_warmth: num,
  tension_trend: str.nullish(),
});
const EmotionTransition = z.object({
  time: str,
  from_state: str,
  to_state: str,
  from_energy: str,
  to_energy: str,
});
const EmotionTrajectory = z.object({
  total_windows: num,
  total_transitions: num,
  total_phases: num,
  unique_states: num,
  narrative: str,
  phases: z.array(EmotionPhase).default([]),
  transitions: z.array(EmotionTransition).default([]),
  trajectory_summary: z.array(TrajectorySummaryPoint).default([]),
});

// --- lyrics ------------------------------------------------------------------
const VaderLine = z.object({ text: str, compound: num, pos: num, neg: num });
const VaderResult = z.object({
  overall_sentiment: num.nullish(),
  line_sentiments: z.array(VaderLine).default([]),
  most_positive: str.nullish(),
  most_negative: str.nullish(),
  note: str.nullish(),
});
const CulturalReference = z.object({ reference: str, tradition: str, significance: str });
const KeyLine = z.object({ line: str, significance: str });
const SemanticResult = z.object({
  method: str.nullish(),
  themes: z.array(str).nullish(),
  imagery: z.array(str).nullish(),
  cultural_references: z.array(CulturalReference).nullish(),
  emotional_arc: str.nullish(),
  subtext: str.nullish(),
  surface_vs_depth: str.nullish(),
  semantic_valence: num.nullish(),
  key_lines: z.array(KeyLine).nullish(),
  error: str.nullish(),
  prompt_template: z.array(str).nullish(),
});
const InterpretationGap = z.object({
  vader_surface: num,
  semantic_depth: num,
  gap: num,
  description: str,
});
const LyricsAnalysis = z.object({
  available: z.boolean(),
  source: str.nullish(),
  line_count: num.nullish(),
  text: str.nullish(),
  vader: VaderResult.nullish(),
  semantic: SemanticResult.nullish(),
  interpretation_gap: InterpretationGap.nullish(),
});

// --- story -------------------------------------------------------------------
const StoryMoment = z.object({
  time: num,
  label: str,
  lyric: str,
  duration: num,
  alignment_confidence: num,
  vocal_relationship: str,
  emotion: str,
  warmth: num,
  chord: str,
  vessel: str,
});
const StoryReading = z.object({
  total_lines: num,
  lyrics_source: str,
  track: str.nullish(),
  artist: str.nullish(),
  title: str.nullish(),
  duration: num.nullish(),
  story_moments: z.array(StoryMoment).default([]),
});

// --- ai detection ------------------------------------------------------------
const AiVector = z.object({
  score: num,
  signal: str,
  value: num.nullish(),
  human_avg: num.nullish(),
  ai_avg: num.nullish(),
  transitions: num.nullish(),
  span_octaves: num.nullish(),
  breathiness: num.nullish(),
  breath_events: num.nullish(),
  deep_breaths: num.nullish(),
});
const AiDetection = z.object({
  overall_score: num,
  verdict: str,
  confidence: str,
  vectors_available: num,
  vectors_possible: num,
  track: str.nullish(),
  vectors: z.record(z.string(), AiVector).default({}),
  weights: z.record(z.string(), z.number()).default({}),
});

// --- genome ------------------------------------------------------------------
const GenomeVector = z.object({
  vocal_pitch: num,
  vocal_range: num,
  vocal_entropy: num,
  vocal_breathiness: num,
  vocal_presence: num,
  drum_tempo: num,
  drum_regularity: num,
  drum_density: num,
  drum_kick_pct: num,
  bass_movement: num,
  texture_centroid: num,
  texture_harmonic: num,
});

// --- the document ------------------------------------------------------------
export const PerceptionDocumentSchema = z.object({
  schema_version: str,
  track: TrackMeta,
  separation: SeparationInfo.nullish(),
  stems: StemAnalysis.nullish(),
  vocals: VocalAnalysis.nullish(),
  rhythm: RhythmAnalysis.nullish(),
  harmony: HarmonyAnalysis.nullish(),
  timbre: TimbreAnalysis.nullish(),
  spatial: SpatialAnalysis.nullish(),
  structure: StructureAnalysis.nullish(),
  emotion: EmotionTrajectory.nullish(),
  lyrics: LyricsAnalysis.nullish(),
  story: StoryReading.nullish(),
  ai_detection: AiDetection.nullish(),
  genome: GenomeVector.nullish(),
});

export type ProgressEvent = z.infer<typeof ProgressEventSchema>;
export type Job = z.infer<typeof JobSchema>;
export type JobStatus = z.infer<typeof JobStatusSchema>;
export type StepStatus = z.infer<typeof StepStatusSchema>;
export type PerceptionDocument = z.infer<typeof PerceptionDocumentSchema>;
