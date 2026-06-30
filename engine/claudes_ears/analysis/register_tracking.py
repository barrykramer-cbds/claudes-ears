"""Vocal register tracking — chest/head/falsetto/fry transitions across the vocals stem.

The register IS the drama: a shift in physical phonation mechanism serving the lyric.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, TypedDict
import warnings

import librosa
import numpy as np

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path

_SR = 22050
_WINDOW_SEC = 0.5
_HOP = 256
_N_FFT = 2048
#: Pitch/energy fallbacks when the stem carries no voiced frames.
_FALLBACK_MEDIAN = 300.0
_FALLBACK_LOW = 150.0
_FALLBACK_HIGH = 500.0
#: Phases shorter than this are noise, not a real register change.
_MIN_PHASE_S = 1.5


class _Moment(TypedDict, total=False):
    """One analysis window; silence windows omit the spectral/harmonic keys."""

    time: float
    label: str
    register: str
    confidence: float
    f0: float
    energy_db: float
    spectral_slope: float
    harmonic_ratio: float


class _Phase(TypedDict, total=False):
    """A run of consecutive same-register moments."""

    register: str
    start: str
    start_time: float
    end: str
    end_time: float
    duration_s: float
    avg_f0: float


class _Transition(TypedDict):
    """A register change between two non-silence phases."""

    time: str
    from_register: str
    to_register: str
    from_f0: float
    to_f0: float
    direction: str
    drama: str


@dataclass
class _Accum:
    """Mutable phase accumulator while merging consecutive moments."""

    register: str
    start: str
    start_time: float
    f0s: list[float]


def detect_register(
    f0: float,
    spectral_slope: float,
    harmonic_ratio: float,
    energy_db: float,
    singer_median: float = _FALLBACK_MEDIAN,
) -> tuple[str, float]:
    """Classify register from pitch-relative, spectral, and harmonic features.

    Boundaries are relative to the singer's own median pitch, not absolute thresholds.
    """
    if f0 <= 0 or energy_db < -50:
        return "silence", 0.0

    chest = head = falsetto = fry = 0

    pitch_ratio = f0 / (singer_median + 1e-10)
    if pitch_ratio < 0.7:
        chest += 4
    elif pitch_ratio < 0.9:
        chest += 3
        head += 1
    elif pitch_ratio < 1.15:
        head += 3
        chest += 1
    elif pitch_ratio < 1.5:
        head += 2
        falsetto += 1
    elif pitch_ratio < 2.0:
        falsetto += 3
        head += 1
    else:
        falsetto += 4

    if spectral_slope < -3.0:
        chest += 2
    elif spectral_slope < -1.5:
        chest += 1
        head += 1
    elif spectral_slope < -0.5:
        head += 1
    else:
        falsetto += 1

    if harmonic_ratio > 0.85:
        chest += 1
    elif harmonic_ratio < 0.5:
        falsetto += 1

    if f0 < 90 and energy_db < -30:
        fry += 4
    elif f0 < 120 and energy_db < -35:
        fry += 3

    scores = {"chest": chest, "head": head, "falsetto": falsetto, "fry": fry}
    register = max(scores, key=lambda r: scores[r])
    total = sum(scores.values())
    confidence = scores[register] / total if total > 0 else 0.0
    return register, round(confidence, 3)


def _label(t: float) -> str:
    """Format a time in seconds as ``m:ss``."""
    return f"{int(t // 60)}:{int(t % 60):02d}"


def _silence_moment(t_center: float, energy_db: float) -> _Moment:
    """Build a silence moment (drops the spectral/harmonic keys per schema §5)."""
    return {
        "time": round(t_center, 2),
        "label": _label(t_center),
        "register": "silence",
        "confidence": 0.0,
        "f0": 0.0,
        "energy_db": round(energy_db, 1),
    }


def _analyze_window(
    seg: np.ndarray,
    seg_f0: np.ndarray,
    t_center: float,
    energy_db: float,
    sr: int,
    singer_median: float,
) -> _Moment:
    """Classify a single voiced window into a full register moment."""
    mean_f0 = float(np.mean(seg_f0))

    spectrum = np.mean(np.abs(librosa.stft(seg, n_fft=_N_FFT, hop_length=_HOP)), axis=1)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=_N_FFT)
    valid = (freqs > 80) & (spectrum > 0)
    if np.sum(valid) > 10:
        slope = float(np.polyfit(np.log10(freqs[valid]), np.log10(spectrum[valid] + 1e-10), 1)[0])
    else:
        slope = -2.0

    harm = librosa.effects.harmonic(seg)
    harmonic_ratio = float(np.sum(harm**2)) / (float(np.sum(seg**2)) + 1e-10)

    register, confidence = detect_register(mean_f0, slope, harmonic_ratio, energy_db, singer_median)
    return {
        "time": round(t_center, 2),
        "label": _label(t_center),
        "register": register,
        "confidence": confidence,
        "f0": round(mean_f0, 1),
        "spectral_slope": round(slope, 3),
        "harmonic_ratio": round(harmonic_ratio, 4),
        "energy_db": round(energy_db, 1),
    }


def _voiced_mean(f0s: list[float]) -> float:
    """Mean of the voiced (>0) f0 values, or 0.0 when the run is all silence."""
    voiced = [f for f in f0s if f > 0]
    return round(float(np.mean(voiced)), 1) if voiced else 0.0


def _build_phases(moments: list[_Moment]) -> list[_Phase]:
    """Merge consecutive same-register moments into phases."""
    if not moments:
        return []

    phases: list[_Phase] = []
    first = moments[0]
    cur = _Accum(first["register"], first["label"], first["time"], [first["f0"]])
    for m in moments[1:]:
        if m["register"] == cur.register:
            cur.f0s.append(m["f0"])
            continue
        phases.append(
            {
                "register": cur.register,
                "start": cur.start,
                "start_time": cur.start_time,
                "end": m["label"],
                "end_time": m["time"],
                "duration_s": round(m["time"] - cur.start_time, 1),
                "avg_f0": _voiced_mean(cur.f0s),
            }
        )
        cur = _Accum(m["register"], m["label"], m["time"], [m["f0"]])

    last = moments[-1]
    phases.append(
        {
            "register": cur.register,
            "start": cur.start,
            "start_time": cur.start_time,
            "end": last["label"],
            "end_time": last["time"],
            "duration_s": round(last["time"] - cur.start_time, 1),
            "avg_f0": _voiced_mean(cur.f0s),
        }
    )
    return phases


def _filter_short_phases(phases: list[_Phase]) -> list[_Phase]:
    """Drop sub-threshold phases, merging them into the preceding non-silence phase."""
    kept: list[_Phase] = []
    for p in phases:
        if p["register"] == "silence" or p["duration_s"] >= _MIN_PHASE_S:
            kept.append(p)
        elif kept and kept[-1]["register"] != "silence":
            kept[-1]["end"] = p["end"]
            kept[-1]["end_time"] = p["end_time"]
            kept[-1]["duration_s"] = round(p["end_time"] - kept[-1]["start_time"], 1)
    return kept


def _characterize(from_reg: str, to_reg: str) -> tuple[str, str]:
    """Return (direction, drama) for a register change."""
    if from_reg == "chest" and to_reg in ("head", "falsetto"):
        return "ascending", "lift"
    if from_reg in ("head", "falsetto") and to_reg == "chest":
        return "descending", "drop"
    if from_reg == "head" and to_reg == "falsetto":
        return "ascending", "reach"
    if from_reg == "falsetto" and to_reg == "head":
        return "descending", "return"
    if from_reg == "chest" and to_reg == "fry":
        return "descending", "creak"
    return "lateral", "shift"


def _build_transitions(phases: list[_Phase]) -> list[_Transition]:
    """Emit a transition for each adjacent pair of non-silence phases."""
    transitions: list[_Transition] = []
    for a, b in pairwise(phases):
        if a["register"] == "silence" or b["register"] == "silence":
            continue
        direction, drama = _characterize(a["register"], b["register"])
        transitions.append(
            {
                "time": b["start"],
                "from_register": a["register"],
                "to_register": b["register"],
                "from_f0": a["avg_f0"],
                "to_f0": b["avg_f0"],
                "direction": direction,
                "drama": drama,
            }
        )
    return transitions


def _singer_range(f0_full: np.ndarray) -> tuple[float, float, float]:
    """Return (median, p10, p90) of voiced pitch, or fallbacks when none is voiced."""
    voiced = f0_full[f0_full > 0]
    if len(voiced) == 0:
        return _FALLBACK_MEDIAN, _FALLBACK_LOW, _FALLBACK_HIGH
    return (
        float(np.median(voiced)),
        float(np.percentile(voiced, 10)),
        float(np.percentile(voiced, 90)),
    )


def analyze(audio: Path) -> dict[str, object]:
    """Track chest/head/falsetto/fry register across the vocals stem."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        y, sr_raw = librosa.load(audio, sr=_SR, mono=True)
        sr = int(sr_raw)
        duration = float(librosa.get_duration(y=y, sr=sr))
        f0_full, _, _ = librosa.pyin(y, fmin=60, fmax=1200, sr=sr, hop_length=_HOP)
        f0_full = np.nan_to_num(f0_full, nan=0.0)

        singer_median, singer_low, singer_high = _singer_range(f0_full)

        ws = int(_WINDOW_SEC * sr)
        hs = int(_WINDOW_SEC * sr / 2)
        moments: list[_Moment] = []
        pos = 0
        while pos + ws <= len(y):
            seg = y[pos : pos + ws]
            t_center = (pos + ws / 2) / sr
            rms = float(np.sqrt(np.mean(seg**2)))
            energy_db = float(20 * np.log10(rms + 1e-10))

            seg_f0 = f0_full[pos // _HOP : min((pos + ws) // _HOP, len(f0_full))]
            voiced = seg_f0[seg_f0 > 0]
            if rms < 0.002 or len(voiced) < 3:
                moments.append(_silence_moment(t_center, energy_db))
            else:
                moments.append(_analyze_window(seg, voiced, t_center, energy_db, sr, singer_median))
            pos += hs

    phases = _filter_short_phases(_build_phases(moments))
    transitions = _build_transitions(phases)

    voiced_phases = [p for p in phases if p["register"] != "silence"]
    durations: dict[str, float] = {}
    for p in voiced_phases:
        durations[p["register"]] = durations.get(p["register"], 0.0) + p["duration_s"]
    total_vocal = sum(durations.values())
    distribution = (
        {r: round(d / total_vocal * 100, 1) for r, d in durations.items()}
        if total_vocal > 0
        else {}
    )

    results: dict[str, object] = {
        "duration": round(duration, 2),
        "singer_median_f0": singer_median,
        "singer_range_low": singer_low,
        "singer_range_high": singer_high,
        "total_register_phases": len(voiced_phases),
        "total_transitions": len(transitions),
        "register_distribution": distribution,
        "phases": phases,
        "transitions": transitions[:50],
        "moments": moments,
    }
    clean = sanitize(results)
    assert isinstance(clean, dict)
    return clean
