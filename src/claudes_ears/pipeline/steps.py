"""The frozen step registry — pipeline order + wiring (Lead-only, re-gates on edit).

analyze() input convention is encoded by each Step's InputKind + depends_on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class Phase(Enum):
    """Pipeline phase — also the orchestrated execution order."""

    SEPARATION = auto()
    STEM = auto()
    VOCAL = auto()
    FULL_MIX = auto()
    DERIVED = auto()
    LIBRARY = auto()
    PAIR = auto()


class InputKind(Enum):
    """What a step's ``analyze()`` consumes — tells the orchestrator what to pass."""

    AUDIO_FULL = auto()  # the source mix
    AUDIO_VOCALS = auto()  # demucs vocals stem
    AUDIO_DRUMS = auto()  # demucs drums stem
    AUDIO_OTHER = auto()  # demucs other stem
    STEM_DIR = auto()  # the stem directory
    UPSTREAM = auto()  # single dep: that dict; multi dep: {dep_name: dict}
    LIBRARY = auto()  # cross-track list / library dict + metadata
    PAIR = auto()  # two PerceptionDocuments


#: Phases the orchestrator runs once per track (drives ProgressEvent.total).
_PER_TRACK_PHASES = frozenset(
    {Phase.SEPARATION, Phase.STEM, Phase.VOCAL, Phase.FULL_MIX, Phase.DERIVED}
)


@dataclass(frozen=True, slots=True)
class Step:
    """One registry entry: a module and how the orchestrator wires it."""

    name: str
    module: str  # dotted import path to the analysis module
    phase: Phase
    input: InputKind
    depends_on: tuple[str, ...] = field(default_factory=tuple)
    optional: bool = False

    @property
    def orchestrated(self) -> bool:
        """True if the orchestrator runs this step once per track."""
        return self.phase in _PER_TRACK_PHASES


_A = "claudes_ears.analysis."

#: Ordered, frozen registry. Order IS the orchestrated execution order.
STEPS: tuple[Step, ...] = (
    # --- Phase 1: separation -------------------------------------------------
    Step("separation", "claudes_ears.separation.separate", Phase.SEPARATION, InputKind.AUDIO_FULL),
    # --- Phase 2: stem analysis ----------------------------------------------
    Step("analyze_stems", _A + "analyze_stems", Phase.STEM, InputKind.STEM_DIR, ("separation",)),
    Step(
        "freq_interaction",
        _A + "freq_interaction",
        Phase.STEM,
        InputKind.STEM_DIR,
        ("separation",),
        optional=True,
    ),
    Step(
        "groove_timing",
        _A + "groove_timing",
        Phase.STEM,
        InputKind.AUDIO_DRUMS,
        ("separation",),
        optional=True,
    ),
    Step(
        "timbral_decomposition",
        _A + "timbral_decomposition",
        Phase.STEM,
        InputKind.AUDIO_OTHER,
        ("separation",),
        optional=True,
    ),
    # --- Phase 2c/2d: vocal --------------------------------------------------
    Step(
        "vocal_layers",
        _A + "vocal_layers",
        Phase.VOCAL,
        InputKind.AUDIO_VOCALS,
        ("separation",),
        optional=True,
    ),
    Step(
        "vocal_intervals",
        _A + "vocal_intervals",
        Phase.VOCAL,
        InputKind.AUDIO_VOCALS,
        ("separation",),
        optional=True,
    ),
    Step(
        "vocal_narrative",
        _A + "vocal_narrative",
        Phase.VOCAL,
        InputKind.AUDIO_VOCALS,
        ("separation",),
        optional=True,
    ),
    Step(
        "vocal_relationships",
        _A + "vocal_relationships",
        Phase.VOCAL,
        InputKind.AUDIO_VOCALS,
        ("separation",),
        optional=True,
    ),
    Step(
        "register_tracking",
        _A + "register_tracking",
        Phase.VOCAL,
        InputKind.AUDIO_VOCALS,
        ("separation",),
        optional=True,
    ),
    Step(
        "breath_detection",
        _A + "breath_detection",
        Phase.VOCAL,
        InputKind.AUDIO_VOCALS,
        ("separation",),
        optional=True,
    ),
    # --- Phase 3: full mix ---------------------------------------------------
    Step("stereo_field", _A + "stereo_field", Phase.FULL_MIX, InputKind.AUDIO_FULL),
    Step(
        "temporal_segmentation", _A + "temporal_segmentation", Phase.FULL_MIX, InputKind.AUDIO_FULL
    ),
    Step("depth_reverb", _A + "depth_reverb", Phase.FULL_MIX, InputKind.AUDIO_FULL),
    Step("chord_progression", _A + "chord_progression", Phase.FULL_MIX, InputKind.AUDIO_FULL),
    # --- Phase 4: derived (take upstream dicts) ------------------------------
    Step(
        "harmonic_rhythm",
        _A + "harmonic_rhythm",
        Phase.DERIVED,
        InputKind.UPSTREAM,
        ("chord_progression",),
    ),
    Step(
        "music_theory",
        _A + "music_theory",
        Phase.DERIVED,
        InputKind.UPSTREAM,
        ("chord_progression",),
    ),
    Step(
        "emotional_trajectory",
        _A + "emotional_trajectory",
        Phase.DERIVED,
        InputKind.UPSTREAM,
        ("temporal_segmentation",),
    ),
    Step(
        "semantic_lyrics",
        _A + "semantic_lyrics",
        Phase.DERIVED,
        InputKind.UPSTREAM,
        ("separation",),
        optional=True,
    ),
    Step(
        "story_reader",
        _A + "story_reader",
        Phase.DERIVED,
        InputKind.UPSTREAM,
        (
            "vocal_relationships",
            "emotional_trajectory",
            "music_theory",
            "chord_progression",
            "temporal_segmentation",
        ),
        optional=True,
    ),
    Step(
        "ai_detector",
        _A + "ai_detector",
        Phase.DERIVED,
        InputKind.STEM_DIR,
        ("vocal_relationships", "register_tracking", "breath_detection", "analyze_stems"),
        optional=True,
    ),
    # --- Phase 5: library / pair (standalone — not run per track) ------------
    Step(
        "genome_map",
        _A + "genome_map",
        Phase.LIBRARY,
        InputKind.LIBRARY,
        ("analyze_stems",),
        optional=True,
    ),
    Step(
        "temporal_genome",
        _A + "temporal_genome",
        Phase.LIBRARY,
        InputKind.LIBRARY,
        ("genome_map",),
        optional=True,
    ),
    Step(
        "version_compare",
        _A + "version_compare",
        Phase.PAIR,
        InputKind.PAIR,
        optional=True,
    ),
)

#: Lookup by step name.
STEP_BY_NAME: dict[str, Step] = {step.name: step for step in STEPS}

#: The per-track steps the orchestrator runs, in order (ProgressEvent.total).
ORCHESTRATED_STEPS: tuple[Step, ...] = tuple(step for step in STEPS if step.orchestrated)

#: Frozen contract: the orchestrated count is the SSE total a re-gate must preserve.
ORCHESTRATED_STEP_COUNT = 21


def _validate_registry() -> None:
    """Fail fast at import on a malformed or wrongly-reordered registry."""
    names = [step.name for step in STEPS]
    if len(names) != len(set(names)):
        msg = "Duplicate step names in the registry"
        raise ValueError(msg)
    seen: set[str] = set()
    for step in STEPS:
        unknown = set(step.depends_on) - set(names)
        if unknown:
            msg = f"Step {step.name!r} depends on unknown steps: {sorted(unknown)}"
            raise ValueError(msg)
        not_yet = set(step.depends_on) - seen
        if not_yet:
            msg = f"Step {step.name!r} depends on later steps: {sorted(not_yet)}"
            raise ValueError(msg)
        seen.add(step.name)
    if len(ORCHESTRATED_STEPS) != ORCHESTRATED_STEP_COUNT:
        msg = (
            f"Expected {ORCHESTRATED_STEP_COUNT} orchestrated steps, got {len(ORCHESTRATED_STEPS)}"
        )
        raise ValueError(msg)
    misfiled = [s.name for s in STEPS if s.orchestrated == (s.phase in {Phase.LIBRARY, Phase.PAIR})]
    if misfiled:
        msg = f"Phase/orchestration mismatch for steps: {misfiled}"
        raise ValueError(msg)


_validate_registry()
