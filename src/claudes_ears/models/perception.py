"""Frozen per-track PerceptionDocument contract (schema.md §2/§5): every domain is
``| None`` (ISSUE-008); reserved-word keys are alias-mapped via ``by_alias``.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"


class _M(BaseModel):
    """Shared base: ignore unmapped raw keys, accept field-name or alias."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# Track + separation
class TrackMeta(_M):
    id: str  # stem-folder name — the universal join key
    source_path: str
    analyzed_at: datetime
    pipeline_version: str
    title: str | None = None
    artist: str | None = None
    duration_s: float | None = None
    sample_rate: int | None = None
    # Per-track metadata (ISSUE-014) — these become DuckDB columns and feed
    # temporal_genome instead of a hardcoded dict.
    year: int | None = None
    genre: str | None = None
    era: str | None = None


class SeparationInfo(_M):
    stems_present: list[str] = Field(default_factory=list)
    stem_dir: str
    model: str | None = None


# Stems (analyze_stems) — genome-vector source
class KitBalance(_M):
    kick: float
    snare: float
    hihat: float


class VocalsStem(_M):
    duration: float
    breathiness: float
    breathiness_desc: str
    dynamic_range_db: float
    stem: str | None = None
    pitch_mean_hz: float | None = None
    pitch_range_semitones: float | None = None
    voiced_fraction: float | None = None
    vocal_melodic_entropy: float | None = None


class DrumsStem(_M):
    duration: float
    tempo_bpm: float
    onsets_per_second: float
    kit_balance: KitBalance
    stem: str | None = None
    beat_regularity: float | None = None


class BassStem(_M):
    duration: float
    dominant_notes: list[str] = Field(default_factory=list)
    root_movement_rate: float
    root_movement_desc: str
    stem: str | None = None


class OtherStem(_M):
    duration: float
    centroid_hz: float
    bandwidth_hz: float
    texture: str
    harmonic_pct: float
    attack: str
    stem: str | None = None


class StemAnalysis(_M):
    vocals: VocalsStem | None = None
    drums: DrumsStem | None = None
    bass: BassStem | None = None
    other: OtherStem | None = None


# Vocals
class Echo(_M):
    delay_s: float
    strength: float


class DenseRegion(_M):
    start: float
    end: float
    density: float


class VocalLayers(_M):
    duration: float
    layering: str
    echo_detected: bool
    harmonic_peaks_mean: float | None = None
    harmonic_peaks_p90: float | None = None
    echo_count: int | None = None
    echoes: list[Echo] | None = None
    echo_desc: str | None = None
    dense_regions: list[DenseRegion] | None = None
    layering_pct: float | None = None


class IntervalProfileEntry(_M):
    semitones: int
    name: str
    meaning: str
    count: int
    pct: float


class SampleInterval(_M):
    time: float
    interval: int
    semitones_raw: int


class DominantInterval(_M):
    name: str
    meaning: str
    pct: float


class VocalIntervals(_M):
    duration: float
    total_interval_events: int
    consonance_ratio: float
    harmonic_character: str
    interval_profile: list[IntervalProfileEntry] = Field(default_factory=list)
    sample_intervals: list[SampleInterval] = Field(default_factory=list)
    dominant_interval: DominantInterval | None = None


class NarrativeSegment(_M):
    # Always present; silence frames drop peak_max / pitch_mean / harmonic_ratio.
    time: float
    label: str
    type: str
    energy_db: float
    peak_count: float
    pitch_spread: float
    spectral_width: float
    solo_score: float
    chorus_score: float
    peak_max: float | None = None
    pitch_mean: float | None = None
    harmonic_ratio: float | None = None


class NarrativePhase(_M):
    type: str
    start: str
    start_time: float
    end: str
    end_time: float
    duration_s: float
    avg_energy: float
    avg_peaks: float


class CallResponse(_M):
    call_time: str
    call_type: str
    response_time: str
    response_type: str
    pattern: str


class VocalNarrative(_M):
    duration: float
    total_phases: int
    total_call_response: int
    type_distribution: dict[str, float] = Field(default_factory=dict)
    phases: list[NarrativePhase] = Field(default_factory=list)
    call_response_patterns: list[CallResponse] = Field(default_factory=list)
    segments: list[NarrativeSegment] = Field(default_factory=list)


class RelationshipMoment(_M):
    # silence / instrumental frames drop lead_pct / below_pct / above_pct.
    time: float
    label: str
    relationship: str
    energy_db: float
    density: int
    density_change: int
    lead_present: bool
    support_register: str
    narrative: str
    lead_pct: float | None = None
    below_pct: float | None = None
    above_pct: float | None = None


class RelationshipStory(_M):
    relationship: str
    narrative: str
    start: str
    start_time: float
    end: str
    duration_s: float
    avg_density: float


class RelationshipTransition(_M):
    time: str
    from_: str = Field(alias="from")
    to: str
    from_narrative: str
    to_narrative: str


class VocalRelationships(_M):
    duration: float
    lead_pitch_center: float
    total_story_phases: int
    total_transitions: int
    relationship_distribution: dict[str, float] = Field(default_factory=dict)
    story: list[RelationshipStory] = Field(default_factory=list)
    transitions: list[RelationshipTransition] = Field(default_factory=list)
    moments: list[RelationshipMoment] = Field(default_factory=list)


class RegisterMoment(_M):
    # silence frames drop spectral_slope / harmonic_ratio.
    time: float
    label: str
    register_: str = Field(alias="register")  # 'register' shadows ABCMeta.register
    confidence: float
    f0: float
    energy_db: float
    spectral_slope: float | None = None
    harmonic_ratio: float | None = None


class RegisterPhase(_M):
    register_: str = Field(alias="register")  # 'register' shadows ABCMeta.register
    start: str
    start_time: float
    end: str
    end_time: float
    duration_s: float
    avg_f0: float | None = None


class RegisterTransition(_M):
    time: str
    from_register: str
    to_register: str
    from_f0: float
    to_f0: float
    direction: str
    drama: str


class RegisterTracking(_M):
    duration: float
    singer_median_f0: float
    singer_range_low: float
    singer_range_high: float
    total_register_phases: int
    total_transitions: int
    register_distribution: dict[str, float] = Field(default_factory=dict)
    phases: list[RegisterPhase] = Field(default_factory=list)
    transitions: list[RegisterTransition] = Field(default_factory=list)
    moments: list[RegisterMoment] = Field(default_factory=list)


class BreathEvent(_M):
    time: float
    end: float
    duration_s: float
    label: str
    depth: str
    avg_flatness: float
    avg_energy_db: float
    avg_centroid: float
    context: str


class DepthDistribution(_M):
    deep: int
    normal: int
    catch: int


class BreathDetection(_M):
    duration: float
    total_breaths: int
    breaths_per_minute: float
    avg_breath_duration_s: float
    avg_inter_breath_interval_s: float
    avg_phrase_duration_s: float
    longest_phrase_s: float
    depth_distribution: DepthDistribution
    context_distribution: dict[str, int] = Field(default_factory=dict)
    breath_events: list[BreathEvent] = Field(default_factory=list)
    phrase_durations: list[float] = Field(default_factory=list)
    # Absent in the empty-result variant.
    min_inter_breath_interval_s: float | None = None
    max_inter_breath_interval_s: float | None = None


class VocalAnalysis(_M):
    layers: VocalLayers | None = None
    intervals: VocalIntervals | None = None
    narrative: VocalNarrative | None = None
    relationships: VocalRelationships | None = None
    # 'register' shadows ABCMeta.register; alias keeps the contract key.
    register_: RegisterTracking | None = Field(default=None, alias="register")
    breath: BreathDetection | None = None


# Rhythm
class TimingDistribution(_M):
    behind_pct: float
    on_grid_pct: float
    ahead_pct: float


class GrooveTiming(_M):
    # Early-exit variants keep only duration/tempo/beat_count + error.
    duration: float
    tempo: float
    beat_count: int
    mean_deviation_ms: float | None = None
    std_deviation_ms: float | None = None
    median_deviation_ms: float | None = None
    feel: str | None = None
    tightness: str | None = None
    swing_ratio: float | None = None
    swing_character: str | None = None
    drift_quarters_ms: list[float] | None = None
    drift: str | None = None
    timing_distribution: TimingDistribution | None = None
    error: str | None = None


class RhythmAnalysis(_M):
    groove: GrooveTiming | None = None


# Harmony
class ChordSegment(_M):
    chord: str
    start: float
    start_beat: int
    end: float
    end_beat: int
    duration_beats: int
    avg_confidence: float


class ChordPattern(_M):
    pattern: str
    count: int


class Modulation(_M):
    time: float
    from_: str = Field(alias="from")
    to: str


class ChordProgression(_M):
    tempo: float
    total_beats: int
    total_segments: int
    unique_chords: int
    segments: list[ChordSegment] = Field(default_factory=list)
    top_patterns: list[ChordPattern] = Field(default_factory=list)
    modulations: list[Modulation] = Field(default_factory=list)
    chord_sequence_summary: list[str] = Field(default_factory=list)


class HarmonicWindow(_M):
    time: float
    label: str
    changes: int
    changes_per_beat: float
    changes_per_bar: float
    avg_interval_s: float
    rhythm_class: str
    narrative: str


class HarmonicPhase(_M):
    class_: str = Field(alias="class")
    start: str
    start_time: float
    end: str
    end_time: float
    duration_s: float
    avg_changes_per_bar: float
    narrative: str


class AccelerationEvent(_M):
    time: str
    type: str
    from_rate: float
    to_rate: float
    magnitude: float
    narrative: str


class HarmonicRhythm(_M):
    # Degenerate branch carries only total_changes + (normalized) windows.
    total_changes: int
    windows: list[HarmonicWindow] = Field(default_factory=list)
    total_chord_events: int | None = None
    tempo_bpm: float | None = None
    duration: float | None = None
    avg_changes_per_bar: float | None = None
    max_changes_per_bar: float | None = None
    min_changes_per_bar: float | None = None
    harmonic_arc: str | None = None
    total_phases: int | None = None
    total_accel_events: int | None = None
    phases: list[HarmonicPhase] | None = None
    acceleration_events: list[AccelerationEvent] | None = None


class ChordAnalysis(_M):
    numeral: str
    function: str
    tension: float
    color: str
    is_chromatic: bool


class AnalyzedChord(_M):
    chord: str
    start: float
    end: float
    label: str
    analysis: ChordAnalysis | None = None


class Cadence(_M):
    type: str
    strength: str
    narrative: str
    time: float
    label: str
    from_: str = Field(alias="from")
    to: str


class MusicTheory(_M):
    key: str
    mode: str
    key_confidence: float | None = None  # may be NaN at the source → sanitized None
    total_chords: int
    unique_numerals: list[str] = Field(default_factory=list)  # consolidator sorts these
    harmonic_vocabulary_size: int
    chromatic_chords_pct: float
    total_cadences: int
    cadence_distribution: dict[str, int] = Field(default_factory=dict)
    cadences: list[Cadence] = Field(default_factory=list)
    analyzed_chords: list[AnalyzedChord] = Field(default_factory=list)


class HarmonyAnalysis(_M):
    chords: ChordProgression | None = None
    harmonic_rhythm: HarmonicRhythm | None = None
    theory: MusicTheory | None = None


# Timbre
class TopFrequency(_M):
    hz: float
    weight: float


class ActivationPoint(_M):
    time: float
    level: float


class TimbralComponent(_M):
    component: int
    centroid_hz: float
    bandwidth_hz: float
    harmonic_pct: float
    attack_sharpness: float
    attack_type: str
    active_pct: float
    energy_contribution: float
    peak_time: float
    peak_time_label: str
    instrument_guess: str
    classification_confidence: float
    energy_pct: float
    rank: int
    top_frequencies: list[TopFrequency] = Field(default_factory=list)
    activation_envelope: list[ActivationPoint] = Field(default_factory=list)


class TimbralDecomposition(_M):
    duration: float
    n_components: int
    reconstruction_error: float
    components: list[TimbralComponent] = Field(default_factory=list)


class PairBand(_M):
    overlap: float
    correlation: float
    dominance: float
    dominant: str


class FreqPair(_M):
    pair: str
    bands: dict[str, PairBand] = Field(default_factory=dict)
    overall_overlap: float
    competition: str


class FreqInteraction(_M):
    stem_count: int
    pairs: list[FreqPair] = Field(default_factory=list)
    territory: dict[str, dict[str, float]] = Field(default_factory=dict)


class TimbreAnalysis(_M):
    decomposition: TimbralDecomposition | None = None
    interaction: FreqInteraction | None = None


# Spatial
class WidthTimelinePoint(_M):
    time: float
    width: float
    balance: float


class StereoEvent(_M):
    time: float
    type: str
    magnitude: float


class StereoField(_M):
    # Mono variant carries only stereo + note.
    stereo: bool
    note: str | None = None
    duration: float | None = None
    mid_pct: float | None = None
    side_pct: float | None = None
    stereo_width: float | None = None
    width_desc: str | None = None
    lr_balance: float | None = None
    balance_desc: str | None = None
    lr_correlation: float | None = None  # may be NaN at the source → sanitized None
    correlation_desc: str | None = None
    band_width: dict[str, float] | None = None
    widest_band: str | None = None
    narrowest_band: str | None = None
    width_timeline: list[WidthTimelinePoint] | None = None
    stereo_events: list[StereoEvent] | None = None


class DepthReverb(_M):
    duration: float
    rt60_estimate: float
    pre_delay_ms: float
    spectral_persistence: float
    spectral_flatness_mean: float
    spectral_flatness_std: float
    wetness_index: float
    room_size: str
    perceived_distance: str
    spatial_placement: str
    rt60_std: float | None = None


class SpatialAnalysis(_M):
    stereo: StereoField | None = None
    depth: DepthReverb | None = None


# Structure
class Snapshot(_M):
    seg: int
    t_start: float
    t_end: float
    t_center: float
    time: str
    rms_mean: float
    rms_p90: float
    dyn_range: float
    centroid: float
    harm_pct: float
    key: str
    tension: float
    consonance: float
    warmth: float
    onset_density: float
    tempo: float


class PointDb(_M):
    time: str
    db: float


class PointVal(_M):
    time: str
    val: float


class StructureTransition(_M):
    time: str
    type: str
    db: float


class KeyChange(_M):
    time: str
    from_: str = Field(alias="from")
    to: str


class Arc(_M):
    energy: str
    e_thirds: list[float | None] = Field(default_factory=list)  # NaN thirds → None
    t_thirds: list[float | None] = Field(default_factory=list)


class StructureNarrative(_M):
    climax: PointDb | None = None
    quietest: PointDb | None = None
    peak_tension: PointVal | None = None
    transitions: list[StructureTransition] = Field(default_factory=list)
    key_changes: list[KeyChange] = Field(default_factory=list)
    arc: Arc | None = None


class StructureAnalysis(_M):
    snapshots: list[Snapshot] = Field(default_factory=list)
    narrative: StructureNarrative | None = None  # {} at the source → None


# Emotion
class TrajectorySummaryPoint(_M):
    time: str
    state: str
    energy: str


class EmotionPhase(_M):
    state: str
    energy: str
    start: str
    end: str
    duration_s: float
    avg_tension: float
    avg_warmth: float
    tension_trend: str | None = None  # absent on the final phase


class EmotionTransition(_M):
    time: str
    from_state: str
    to_state: str
    from_energy: str
    to_energy: str


class EmotionTrajectory(_M):
    # The {error} variant is collapsed to a null domain by the consolidator.
    total_windows: int
    total_transitions: int
    total_phases: int
    unique_states: int
    narrative: str
    phases: list[EmotionPhase] = Field(default_factory=list)
    transitions: list[EmotionTransition] = Field(default_factory=list)
    trajectory_summary: list[TrajectorySummaryPoint] = Field(default_factory=list)


# Lyrics (semantic_lyrics owns the grounded LLM reading)
class VaderLine(_M):
    text: str
    compound: float
    pos: float
    neg: float


class VaderResult(_M):
    overall_sentiment: float | None = None
    line_sentiments: list[VaderLine] = Field(default_factory=list)
    most_positive: str | None = None
    most_negative: str | None = None
    note: str | None = None


class CulturalReference(_M):
    reference: str
    tradition: str
    significance: str


class KeyLine(_M):
    line: str
    significance: str


class SemanticResult(_M):
    method: str | None = None
    themes: list[str] | None = None
    imagery: list[str] | None = None
    cultural_references: list[CulturalReference] | None = None
    emotional_arc: str | None = None
    subtext: str | None = None
    surface_vs_depth: str | None = None
    semantic_valence: float | None = None
    key_lines: list[KeyLine] | None = None
    error: str | None = None
    prompt_template: list[str] | None = None


class InterpretationGap(_M):
    vader_surface: float
    semantic_depth: float
    gap: float
    description: str


class LyricsAnalysis(_M):
    available: bool
    source: str | None = None
    line_count: int | None = None
    text: str | None = None
    vader: VaderResult | None = None
    semantic: SemanticResult | None = None
    interpretation_gap: InterpretationGap | None = None


# Story (story_reader, rule-based)
class StoryMoment(_M):
    time: float
    label: str
    lyric: str
    duration: float
    alignment_confidence: float
    vocal_relationship: str
    emotion: str
    warmth: float
    chord: str
    vessel: str


class StoryReading(_M):
    total_lines: int
    lyrics_source: str
    track: str | None = None
    artist: str | None = None
    title: str | None = None
    duration: float | None = None
    story_moments: list[StoryMoment] = Field(default_factory=list)


# AI detection
class AiVector(_M):
    # Union of the 7 vector shapes; only score + signal are universal.
    score: float
    signal: str
    value: float | None = None
    human_avg: float | None = None
    ai_avg: float | None = None
    transitions: int | None = None
    span_octaves: float | None = None
    breathiness: float | None = None
    breath_events: int | None = None
    deep_breaths: int | None = None


class AiDetection(_M):
    overall_score: float
    verdict: str
    confidence: str
    vectors_available: int
    vectors_possible: int
    track: str | None = None
    vectors: dict[str, AiVector] = Field(default_factory=dict)
    weights: dict[str, float] = Field(default_factory=dict)


# Genome (12-dim DuckDB VSS contract)
class GenomeVector(_M):
    vocal_pitch: float
    vocal_range: float
    vocal_entropy: float
    vocal_breathiness: float
    vocal_presence: float
    drum_tempo: float
    drum_regularity: float
    drum_density: float
    drum_kick_pct: float
    bass_movement: float
    texture_centroid: float
    texture_harmonic: float

    #: Canonical dimension order — must match the DuckDB ``FLOAT[12]`` column.
    DIMS: ClassVar[tuple[str, ...]] = (
        "vocal_pitch",
        "vocal_range",
        "vocal_entropy",
        "vocal_breathiness",
        "vocal_presence",
        "drum_tempo",
        "drum_regularity",
        "drum_density",
        "drum_kick_pct",
        "bass_movement",
        "texture_centroid",
        "texture_harmonic",
    )

    def as_list(self) -> list[float]:
        """Return the 12 dims in canonical order for VSS insertion."""
        return [float(getattr(self, dim)) for dim in self.DIMS]


# The document
class PerceptionDocument(_M):
    """One consolidated, validated document per analyzed track."""

    schema_version: str = SCHEMA_VERSION
    track: TrackMeta
    separation: SeparationInfo | None = None
    stems: StemAnalysis | None = None
    vocals: VocalAnalysis | None = None
    rhythm: RhythmAnalysis | None = None
    harmony: HarmonyAnalysis | None = None
    timbre: TimbreAnalysis | None = None
    spatial: SpatialAnalysis | None = None
    structure: StructureAnalysis | None = None
    emotion: EmotionTrajectory | None = None
    lyrics: LyricsAnalysis | None = None
    story: StoryReading | None = None
    ai_detection: AiDetection | None = None
    # All-or-nothing: consolidator sets this None unless all 12 dims are finite.
    genome: GenomeVector | None = None
