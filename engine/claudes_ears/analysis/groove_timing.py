"""Groove / micro-timing: where hits land against the grid — feel, swing, drift."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import librosa
import numpy as np
import numpy.typing as npt

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path

FloatArray = npt.NDArray[np.float64]


def analyze(audio: Path, sr: int = 22050) -> dict[str, object]:
    """Measure beat deviation, feel, swing and drift from the drums stem."""
    y, _ = librosa.load(str(audio), sr=sr, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = float(np.atleast_1d(tempo)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    base: dict[str, object] = {
        "duration": round(duration, 2),
        "tempo": round(tempo_val, 1),
        "beat_count": len(beat_times),
    }

    # Shape 1: too few beats to define a grid at all.
    if len(beat_times) < 4:
        return _finalize({**base, "error": "insufficient beats detected"})

    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=False)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    deviations = _beat_deviations(onset_times, beat_times, tempo_val)

    # Shape 2: a grid exists but not enough onsets land near it to be meaningful.
    if len(deviations) < 10:
        return _finalize({**base, "error": "insufficient onset-beat pairs"})

    # Shape 3: full reading.
    mean_dev = round(float(np.mean(deviations)), 3)
    std_dev = round(float(np.std(deviations)), 3)
    result: dict[str, object] = {
        **base,
        "mean_deviation_ms": mean_dev,
        "std_deviation_ms": std_dev,
        "median_deviation_ms": round(float(np.median(deviations)), 3),
        "feel": _feel(mean_dev),
        "tightness": _tightness(std_dev),
    }
    result.update(_swing(onset_times))
    result.update(_drift(deviations))
    result["timing_distribution"] = _distribution(deviations)
    return _finalize(result)


def _finalize(result: dict[str, object]) -> dict[str, object]:
    """Sanitize for JSON; sanitize preserves the dict shape, so the cast is safe."""
    return cast("dict[str, object]", sanitize(result))


def _beat_deviations(onsets: FloatArray, beats: FloatArray, tempo: float) -> FloatArray:
    """Signed onset-to-nearest-beat offsets (ms), dropping hits past a half-beat away."""
    half_beat_ms = (60.0 / tempo) * 500.0
    devs: list[float] = []
    for onset in onsets:
        nearest = beats[int(np.argmin(np.abs(beats - onset)))]
        dev_ms = float((onset - nearest) * 1000.0)
        if abs(dev_ms) < half_beat_ms:
            devs.append(dev_ms)
    return np.asarray(devs, dtype=np.float64)


def _feel(mean_dev_ms: float) -> str:
    if mean_dev_ms > 5:
        return "behind the beat (lazy / heavy / groove)"
    if mean_dev_ms > 2:
        return "slightly behind (relaxed feel)"
    if mean_dev_ms < -5:
        return "ahead of the beat (pushing / anxious / urgent)"
    if mean_dev_ms < -2:
        return "slightly ahead (driving feel)"
    return "on the grid (mechanical / precise)"


def _tightness(std_dev_ms: float) -> str:
    if std_dev_ms < 5:
        return "machine-tight (quantized or extremely precise)"
    if std_dev_ms < 10:
        return "tight (skilled performer)"
    if std_dev_ms < 20:
        return "human (natural variation)"
    if std_dev_ms < 35:
        return "loose (deliberate or amateur)"
    return "very loose (freeform or intentionally sloppy)"


def _swing(onsets: FloatArray) -> dict[str, object]:
    """Mean long/short ratio over consecutive onset-interval pairs; empty if undetectable."""
    if len(onsets) <= 20:
        return {}
    intervals = np.diff(onsets) * 1000.0
    ratios: list[float] = []
    for i in range(0, len(intervals) - 1, 2):
        a, b = float(intervals[i]), float(intervals[i + 1])
        ratio = max(a, b) / (min(a, b) + 1e-10)
        if 0.8 < ratio < 3.0:
            ratios.append(ratio)
    if not ratios:
        return {}
    avg = float(np.mean(ratios))
    return {"swing_ratio": round(avg, 4), "swing_character": _swing_character(avg)}


def _swing_character(ratio: float) -> str:
    if ratio > 1.6:
        return "heavy swing (jazz / shuffle)"
    if ratio > 1.3:
        return "moderate swing (bouncy feel)"
    if ratio > 1.1:
        return "slight swing (subtle groove)"
    return "straight (no swing)"


def _drift(deviations: FloatArray) -> dict[str, object]:
    """Per-quarter mean deviation and a label for drift across the take; empty if too short."""
    if len(deviations) <= 20:
        return {}
    q = len(deviations) // 4
    quarters = [
        float(np.mean(deviations[:q])),
        float(np.mean(deviations[q : 2 * q])),
        float(np.mean(deviations[2 * q : 3 * q])),
        float(np.mean(deviations[3 * q :])),
    ]
    return {
        "drift_quarters_ms": [round(x, 2) for x in quarters],
        "drift": _drift_label(quarters[-1] - quarters[0]),
    }


def _drift_label(drift_ms: float) -> str:
    if drift_ms > 3:
        return "drifting behind over time (relaxing)"
    if drift_ms < -3:
        return "drifting ahead over time (building urgency)"
    return "stable timing (no drift)"


def _distribution(deviations: FloatArray) -> dict[str, float]:
    """Percent of hits behind / on-grid / ahead, using a +/-2ms grid window."""
    n = len(deviations)
    behind = float(np.sum(deviations > 2)) / n * 100.0
    ahead = float(np.sum(deviations < -2)) / n * 100.0
    return {
        "behind_pct": round(behind, 1),
        "on_grid_pct": round(100.0 - behind - ahead, 1),
        "ahead_pct": round(ahead, 1),
    }
