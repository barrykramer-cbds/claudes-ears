"""Breath detection — where the singer breathes, how deep, and how it shapes phrasing.

Breath is broadband noise: quieter than singing, louder than silence, spectrally flat.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import librosa
import numpy as np

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path

_SR = 22050
_HOP = 512
_MERGE_GAP_FRAMES = 3
_MIN_BREATH_S = 0.10
_MAX_BREATH_S = 1.0


def analyze(audio: Path) -> dict[str, object]:
    """Detect breaths, depth and phrasing in the vocals stem."""
    y, sr = librosa.load(str(audio), sr=_SR, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))
    frame_duration = _HOP / sr

    rms = librosa.feature.rms(y=y, hop_length=_HOP)[0]
    n_frames = len(rms)
    if n_frames == 0:
        return _empty_result(duration)

    rms_sorted = np.sort(rms)
    singing_threshold = float(rms_sorted[n_frames // 2])
    silence_threshold = float(rms_sorted[n_frames // 4])

    # No frame louder than the median means there is no singing to anchor breaths.
    singing_mask = rms > singing_threshold
    if not bool(singing_mask.any()):
        return _empty_result(duration)

    flatness = librosa.feature.spectral_flatness(y=y, hop_length=_HOP)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=_HOP)[0]
    y_harm = librosa.effects.harmonic(y)
    harm_rms = librosa.feature.rms(y=y_harm, hop_length=_HOP)[0]
    harmonic_ratio = harm_rms / (rms + 1e-10)

    breath_rms_low = silence_threshold * 1.5
    breath_rms_high = singing_threshold * 0.6
    breath_flatness_min = float(np.median(flatness[singing_mask])) * 1.7

    breath_frames = [
        i
        for i in range(n_frames)
        if breath_rms_low < rms[i] < breath_rms_high
        and flatness[i] > breath_flatness_min
        and harmonic_ratio[i] < 0.85
    ]
    if not breath_frames:
        return _empty_result(duration)

    events = [
        event
        for start, end in _merge_runs(breath_frames)
        if (
            event := _build_event(
                start, end, frame_duration, n_frames, rms, flatness, centroid, singing_threshold
            )
        )
        is not None
    ]
    if not events:
        return _empty_result(duration)

    return cast("dict[str, object]", sanitize(_summarize(events, duration)))


def _merge_runs(frames: list[int]) -> list[tuple[int, int]]:
    """Group sorted frame indices into (start, end) runs, bridging short gaps."""
    runs: list[tuple[int, int]] = []
    start = prev = frames[0]
    for frame in frames[1:]:
        if frame - prev <= _MERGE_GAP_FRAMES:
            prev = frame
        else:
            runs.append((start, prev))
            start = prev = frame
    runs.append((start, prev))
    return runs


def _build_event(
    start: int,
    end: int,
    frame_duration: float,
    n_frames: int,
    rms: np.ndarray,
    flatness: np.ndarray,
    centroid: np.ndarray,
    singing_threshold: float,
) -> dict[str, object] | None:
    """Validate a frame run by duration and singing context; emit a breath event or None."""
    event_duration = (end - start + 1) * frame_duration
    if not (_MIN_BREATH_S <= event_duration <= _MAX_BREATH_S):
        return None

    context_window = int(1.0 / frame_duration)
    before = bool(np.any(rms[max(0, start - context_window) : start] > singing_threshold))
    after = bool(np.any(rms[end : min(n_frames, end + context_window)] > singing_threshold))
    if not (before or after):
        return None

    start_time = start * frame_duration
    avg_rms = float(np.mean(rms[start : end + 1]))
    if before and after:
        context = "between phrases"
    elif after:
        context = "phrase start"
    else:
        context = "phrase end"
    return {
        "time": round(start_time, 3),
        "end": round((end + 1) * frame_duration, 3),
        "duration_s": round(event_duration, 3),
        "label": f"{int(start_time // 60)}:{int(start_time % 60):02d}",
        "depth": _classify_depth(event_duration),
        "avg_flatness": round(float(np.mean(flatness[start : end + 1])), 5),
        "avg_energy_db": round(float(20 * np.log10(avg_rms + 1e-10)), 1),
        "avg_centroid": round(float(np.mean(centroid[start : end + 1])), 1),
        "context": context,
    }


def _classify_depth(duration_s: float) -> str:
    if duration_s > 0.5:
        return "deep"
    if duration_s > 0.25:
        return "normal"
    return "catch"


def _summarize(events: list[dict[str, object]], duration: float) -> dict[str, object]:
    times = [cast("float", e["time"]) for e in events]
    ends = [cast("float", e["end"]) for e in events]
    intervals = [round(times[i] - ends[i - 1], 3) for i in range(1, len(events))]
    phrases = [round(gap, 2) for gap in intervals if gap > 0]

    depths = {"deep": 0, "normal": 0, "catch": 0}
    contexts: dict[str, int] = {}
    for event in events:
        depths[cast("str", event["depth"])] += 1
        ctx = cast("str", event["context"])
        contexts[ctx] = contexts.get(ctx, 0) + 1

    return {
        "duration": round(duration, 2),
        "total_breaths": len(events),
        "breaths_per_minute": round(len(events) / (duration / 60), 2) if duration > 0 else 0.0,
        "avg_breath_duration_s": round(
            float(np.mean([cast("float", e["duration_s"]) for e in events])), 3
        ),
        "avg_inter_breath_interval_s": round(float(np.mean(intervals)), 2) if intervals else 0.0,
        "min_inter_breath_interval_s": round(float(np.min(intervals)), 2) if intervals else 0.0,
        "max_inter_breath_interval_s": round(float(np.max(intervals)), 2) if intervals else 0.0,
        "avg_phrase_duration_s": round(float(np.mean(phrases)), 2) if phrases else 0.0,
        "longest_phrase_s": round(float(np.max(phrases)), 2) if phrases else 0.0,
        "depth_distribution": depths,
        "context_distribution": contexts,
        "breath_events": events,
        "phrase_durations": phrases[:50],
    }


def _empty_result(duration: float) -> dict[str, object]:
    """The reduced root shape (schema §5): no events, no inter-breath interval keys populated."""
    return {
        "duration": round(duration, 2),
        "total_breaths": 0,
        "breaths_per_minute": 0.0,
        "avg_breath_duration_s": 0.0,
        "avg_inter_breath_interval_s": 0.0,
        "avg_phrase_duration_s": 0.0,
        "longest_phrase_s": 0.0,
        "depth_distribution": {"deep": 0, "normal": 0, "catch": 0},
        "context_distribution": {},
        "breath_events": [],
        "phrase_durations": [],
    }
