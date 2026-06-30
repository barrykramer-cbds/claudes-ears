"""Orchestrator: dependency-order traversal, upstream wiring, skip path, progress.

Drives the registry against injected fake ``analyze`` callables — no real modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from claudes_ears.models.jobs import ProgressEvent, StepStatus
from claudes_ears.pipeline.orchestrator import run_track
from claudes_ears.pipeline.steps import ORCHESTRATED_STEP_COUNT, ORCHESTRATED_STEPS, Step

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest

    from claudes_ears.pipeline.orchestrator import AnalyzeFn, StepResult

#: Valid-enough outputs for the required (non-optional) steps so consolidation passes.
_CANNED: dict[str, dict[str, object]] = {
    "separation": {"stems_present": ["vocals", "drums"], "stem_dir": "/x"},
    "analyze_stems": {},
    "stereo_field": {"stereo": False},
    "temporal_segmentation": {"snapshots": [], "narrative": {}},
    "depth_reverb": {
        "duration": 1.0,
        "rt60_estimate": 0.5,
        "pre_delay_ms": 10.0,
        "spectral_persistence": 0.5,
        "spectral_flatness_mean": 0.3,
        "spectral_flatness_std": 0.1,
        "wetness_index": 0.4,
        "room_size": "medium",
        "perceived_distance": "near",
        "spatial_placement": "center",
    },
    "chord_progression": {
        "tempo": 120.0,
        "total_beats": 4,
        "total_segments": 1,
        "unique_chords": 1,
    },
    "harmonic_rhythm": {"total_changes": 0},
    "music_theory": {
        "key": "C",
        "mode": "major",
        "total_chords": 1,
        "harmonic_vocabulary_size": 1,
        "chromatic_chords_pct": 0.0,
        "total_cadences": 0,
    },
    "emotional_trajectory": {
        "total_windows": 0,
        "total_transitions": 0,
        "total_phases": 0,
        "unique_states": 0,
        "narrative": "flat",
    },
}

_AI_DETECTION = {
    "overall_score": 0.5,
    "verdict": "human",
    "confidence": "low",
    "vectors_available": 1,
    "vectors_possible": 7,
}


def _resolver(
    order: list[str],
    *,
    received: dict[str, tuple[object, ...]] | None = None,
    overrides: dict[str, dict[str, object]] | None = None,
) -> Callable[[Step], AnalyzeFn]:
    """Build a resolver whose fakes record call order/args; optional steps degrade."""
    extra = overrides or {}

    def resolve(step: Step) -> AnalyzeFn:
        def analyze(*args: object) -> StepResult:
            order.append(step.name)
            if received is not None:
                received[step.name] = args
            if step.name in extra:
                return extra[step.name]
            if step.optional:
                raise NotImplementedError(step.name)
            return _CANNED[step.name]

        return analyze

    return resolve


def test_visits_every_step_in_registry_dependency_order() -> None:
    order: list[str] = []
    run_track(Path("/songs/x.mp3"), resolve=_resolver(order))
    assert order == [step.name for step in ORCHESTRATED_STEPS]


def test_derived_step_receives_its_upstream_dict() -> None:
    received: dict[str, tuple[object, ...]] = {}
    run_track(Path("/songs/x.mp3"), resolve=_resolver([], received=received))
    assert received["music_theory"] == (_CANNED["chord_progression"],)


def test_stem_dir_step_with_deps_receives_dir_and_dep_outputs() -> None:
    received: dict[str, tuple[object, ...]] = {}
    run_track(
        Path("/songs/x.mp3"),
        resolve=_resolver([], received=received, overrides={"ai_detector": _AI_DETECTION}),
    )
    stem_dir, deps = received["ai_detector"]
    assert isinstance(stem_dir, Path)
    assert isinstance(deps, dict)
    assert "analyze_stems" in deps
    assert "separation" not in deps


def test_skip_separation_synthesizes_result_without_calling_separate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLAUDES_EARS_STEMS", str(tmp_path))
    stem_dir = tmp_path / "x"
    stem_dir.mkdir()
    (stem_dir / "vocals.wav").touch()
    (stem_dir / "drums.wav").touch()

    order: list[str] = []
    _, results = run_track(Path("/songs/x.mp3"), skip_separation=True, resolve=_resolver(order))

    assert "separation" not in order
    assert results["separation"] == {
        "stems_present": ["drums", "vocals"],
        "stem_dir": str(stem_dir),
    }


def test_progress_events_span_the_full_pipeline() -> None:
    events: list[ProgressEvent] = []
    run_track(Path("/songs/x.mp3"), resolve=_resolver([]), progress=events.append)

    assert all(event.total == ORCHESTRATED_STEP_COUNT for event in events)
    assert sorted({event.index for event in events}) == list(range(1, ORCHESTRATED_STEP_COUNT + 1))
    started = {event.step for event in events if event.status is StepStatus.started}
    assert started == {step.name for step in ORCHESTRATED_STEPS}
