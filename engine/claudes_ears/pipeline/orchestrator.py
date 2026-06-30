"""Drive the registry per-track via in-process ``analyze()`` calls (ISSUE-001: no
subprocess, warm models), feeding upstream dicts to derived steps.
"""

from __future__ import annotations

from datetime import UTC, datetime
import importlib
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from claudes_ears import config
from claudes_ears.models.jobs import ProgressEvent, StepStatus
from claudes_ears.models.perception import PerceptionDocument, TrackMeta
from claudes_ears.pipeline.consolidator import consolidate
from claudes_ears.pipeline.steps import (
    ORCHESTRATED_STEP_COUNT,
    ORCHESTRATED_STEPS,
    InputKind,
    Step,
)

if TYPE_CHECKING:
    from collections.abc import Callable

PIPELINE_VERSION = "0.1.0"

#: Step result kept for the consolidator + as upstream input to later steps.
StepResult = dict[str, object]


class AnalyzeFn(Protocol):
    def __call__(self, *args: object) -> StepResult: ...


def _import_analyze(step: Step) -> AnalyzeFn:
    """Resolve a step's ``analyze`` via its registry dotted path (lazy, patchable)."""
    module = importlib.import_module(step.module)
    return cast("AnalyzeFn", module.analyze)


def run_track(
    audio: Path,
    *,
    job_id: str = "local",
    skip_separation: bool = False,
    resolve: Callable[[Step], AnalyzeFn] = _import_analyze,
    progress: Callable[[ProgressEvent], None] | None = None,
    title: str | None = None,
    artist: str | None = None,
) -> tuple[PerceptionDocument, dict[str, StepResult | None]]:
    """Run the per-track pipeline in dependency order; return (document, raw results)."""
    results: dict[str, StepResult | None] = {}
    stem_dir = config.stems_dir() / audio.stem

    for index, step in enumerate(ORCHESTRATED_STEPS, start=1):
        if step.name == "separation" and skip_separation:
            results[step.name] = _scan_stems(stem_dir)
            _emit(progress, job_id, step, index, StepStatus.skipped)
            continue

        _emit(progress, job_id, step, index, StepStatus.started)
        try:
            analyze = resolve(step)
            args = _call_args(step, audio=audio, stem_dir=stem_dir, results=results)
            results[step.name] = analyze(*args)
        except Exception as error:
            results[step.name] = None
            if not step.optional:
                _emit(progress, job_id, step, index, StepStatus.failed, str(error))
                raise
            _emit(progress, job_id, step, index, StepStatus.skipped, str(error))
            continue

        if step.name == "separation":
            stem_dir = _resolve_stem_dir(results[step.name], stem_dir)
        _emit(progress, job_id, step, index, StepStatus.completed)

    track = _track_meta(audio, results.get("separation"), title=title, artist=artist)
    document = consolidate(track, results)
    return document, results


def _call_args(
    step: Step,
    *,
    audio: Path,
    stem_dir: Path,
    results: dict[str, StepResult | None],
) -> tuple[object, ...]:
    """Build positional args for a step's ``analyze()`` from its InputKind + deps."""
    deps = {name: results.get(name) for name in step.depends_on}
    kind = step.input
    if kind is InputKind.AUDIO_FULL:
        return (audio,)
    if kind is InputKind.AUDIO_VOCALS:
        return (stem_dir / "vocals.wav",)
    if kind is InputKind.AUDIO_DRUMS:
        return (stem_dir / "drums.wav",)
    if kind is InputKind.AUDIO_OTHER:
        return (stem_dir / "other.wav",)
    if kind is InputKind.STEM_DIR:
        extra = {name: result for name, result in deps.items() if name != "separation"}
        return (stem_dir, extra) if extra else (stem_dir,)
    if kind is InputKind.UPSTREAM:
        if len(step.depends_on) == 1:
            return (deps[step.depends_on[0]],)
        return (deps,)
    msg = f"Step {step.name!r} has non-orchestrated input {kind.name}"
    raise ValueError(msg)


def _emit(
    progress: Callable[[ProgressEvent], None] | None,
    job_id: str,
    step: Step,
    index: int,
    status: StepStatus,
    message: str | None = None,
) -> None:
    if progress is None:
        return
    progress(
        ProgressEvent(
            job_id=job_id,
            step=step.name,
            index=index,
            total=ORCHESTRATED_STEP_COUNT,
            status=status,
            message=message,
        )
    )


def _scan_stems(stem_dir: Path) -> StepResult:
    """Synthesize a separation result from existing stems (--skip-demucs path)."""
    present = sorted(path.stem for path in stem_dir.glob("*.wav")) if stem_dir.is_dir() else []
    return {"stems_present": present, "stem_dir": str(stem_dir)}


def _resolve_stem_dir(separation: StepResult | None, fallback: Path) -> Path:
    raw = separation.get("stem_dir") if separation else None
    return Path(raw) if isinstance(raw, str) else fallback


def _track_meta(
    audio: Path,
    separation: StepResult | None,
    *,
    title: str | None,
    artist: str | None,
) -> TrackMeta:
    return TrackMeta(
        id=audio.stem,
        source_path=str(audio),
        analyzed_at=datetime.now(UTC),
        pipeline_version=PIPELINE_VERSION,
        title=title,
        artist=artist,
    )
