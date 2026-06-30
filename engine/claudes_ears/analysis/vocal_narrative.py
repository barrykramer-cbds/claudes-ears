"""Vocal narrative: lead/chorus separation and call-and-response within the vocals stem."""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, cast

import librosa
import numpy as np

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path

_HOP = 512
_N_FFT = 2048
_SILENCE_RMS = 0.005
_PEAK_THRESHOLD = 0.25
_MIN_PITCH_HZ = 80.0


def _count_peaks(frame_norm: np.ndarray, threshold: float) -> int:
    """Count interior local maxima above ``threshold`` in a normalized CQT frame."""
    if frame_norm.size < 3:
        return 0
    interior = frame_norm[1:-1]
    mask = (interior > threshold) & (interior > frame_norm[:-2]) & (interior > frame_norm[2:])
    return int(np.count_nonzero(mask))


def _pitch_spread(pitches: np.ndarray, magnitudes: np.ndarray) -> tuple[float, float]:
    """Return (std, mean) of strong detected pitches across all frames; (0, 0) if none."""
    active: list[float] = []
    for frame_idx in range(pitches.shape[1]):
        frame_mags = magnitudes[:, frame_idx]
        if frame_mags.max() <= 0:  # ISSUE-002: no pitch energy — skip before indexing
            continue
        threshold = float(np.percentile(frame_mags[frame_mags > 0], 50))
        strong = pitches[:, frame_idx][frame_mags > threshold]
        strong = strong[strong > _MIN_PITCH_HZ]
        if strong.size:
            active.extend(strong.tolist())
    if not active:
        return 0.0, 0.0
    return float(np.std(active)), float(np.mean(active))


def _solo_chorus_scores(
    mean_peaks: float, max_peaks: float, n_frames: int, spectral_width: float, harmonic_ratio: float
) -> tuple[float, float]:
    """Score a segment as solo vs chorus from peak density, coherence, flatness, harmonicity."""
    solo = 0
    chorus = 0

    if mean_peaks <= 1.5:
        solo += 4
    elif mean_peaks <= 3.5:
        solo += 3
    elif mean_peaks <= 5.5:
        solo += 1
        chorus += 1
    elif mean_peaks <= 8:
        chorus += 3
    else:
        chorus += 4

    if max_peaks > 8:
        chorus += 3
    elif max_peaks > 5.5:
        chorus += 2
    elif max_peaks > 4:
        chorus += 1
    else:
        solo += 2

    if n_frames > 0 and mean_peaks > 2 and max_peaks > 0:
        coherence = mean_peaks / max_peaks
        if coherence > 0.7:
            solo += 2
        elif coherence < 0.4:
            chorus += 2

    if spectral_width < 0.005:
        solo += 1
    elif spectral_width > 0.05:
        chorus += 1

    if harmonic_ratio > 0.85:
        solo += 1
    elif harmonic_ratio < 0.6:
        chorus += 1

    total = solo + chorus
    if total == 0:
        return 0.5, 0.5
    return solo / total, chorus / total


def _classify(solo_score: float, chorus_score: float) -> str:
    """Map solo/chorus scores to a narrative segment type."""
    if solo_score > 0.58:
        return "solo"
    if chorus_score > 0.70:
        return "chorus"
    if chorus_score > 0.50:
        return "lead_with_backing"
    return "solo"


def _label(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


def _analyze_segment(seg: np.ndarray, sr: int, t_center: float) -> dict[str, object]:
    """Build the per-window segment record from a slice of the vocals waveform."""
    rms = float(np.sqrt(np.mean(seg**2)))
    if rms < _SILENCE_RMS:
        return {
            "time": round(t_center, 2),
            "label": _label(t_center),
            "type": "silence",
            "energy_db": -60,
            "peak_count": 0,
            "pitch_spread": 0,
            "spectral_width": 0,
            "solo_score": 0,
            "chorus_score": 0,
        }

    energy_db = round(20 * np.log10(rms + 1e-10), 2)

    cqt = np.abs(
        librosa.cqt(
            seg,
            sr=sr,
            hop_length=_HOP,
            fmin=librosa.note_to_hz("C2"),
            n_bins=60,
            bins_per_octave=12,
        )
    )
    peak_counts: list[int] = []
    for frame_idx in range(cqt.shape[1]):
        frame = cqt[:, frame_idx]
        peak = frame.max()
        if peak < 0.01:
            continue
        peak_counts.append(_count_peaks(frame / peak, _PEAK_THRESHOLD))

    mean_peaks = float(np.mean(peak_counts)) if peak_counts else 0.0
    max_peaks = float(np.max(peak_counts)) if peak_counts else 0.0

    pitches, magnitudes = librosa.piptrack(y=seg, sr=sr, n_fft=_N_FFT, hop_length=_HOP)
    pitch_spread, pitch_mean = _pitch_spread(pitches, magnitudes)

    spectral_width = float(np.mean(librosa.feature.spectral_flatness(y=seg)[0]))

    y_harm = librosa.effects.harmonic(seg)
    harmonic_ratio = float(np.sum(y_harm**2)) / (float(np.sum(seg**2)) + 1e-10)

    solo_score, chorus_score = _solo_chorus_scores(
        mean_peaks, max_peaks, len(peak_counts), spectral_width, harmonic_ratio
    )
    return {
        "time": round(t_center, 2),
        "label": _label(t_center),
        "type": _classify(solo_score, chorus_score),
        "energy_db": energy_db,
        "peak_count": round(mean_peaks, 1),
        "peak_max": round(max_peaks, 1),
        "pitch_spread": round(pitch_spread, 1),
        "pitch_mean": round(pitch_mean, 1),
        "spectral_width": round(spectral_width, 6),
        "harmonic_ratio": round(harmonic_ratio, 4),
        "solo_score": round(solo_score, 3),
        "chorus_score": round(chorus_score, 3),
    }


def _build_phases(segments: list[dict[str, object]]) -> list[dict[str, object]]:
    """Merge consecutive same-type segments into narrative phases with summary stats."""
    if not segments:
        return []

    phases: list[dict[str, object]] = []
    run_type = segments[0]["type"]
    start = segments[0]
    energies: list[float] = [cast("float", segments[0]["energy_db"])]
    peaks: list[float] = [cast("float", segments[0]["peak_count"])]

    def finalize(boundary: dict[str, object]) -> dict[str, object]:
        start_time = cast("float", start["time"])
        return {
            "type": run_type,
            "start": start["label"],
            "start_time": start_time,
            "end": boundary["label"],
            "end_time": boundary["time"],
            "duration_s": round(cast("float", boundary["time"]) - start_time, 1),
            "avg_energy": round(float(np.mean(energies)), 1),
            "avg_peaks": round(float(np.mean(peaks)), 1),
        }

    for seg in segments[1:]:
        if seg["type"] == run_type:
            energies.append(cast("float", seg["energy_db"]))
            peaks.append(cast("float", seg["peak_count"]))
            continue
        phases.append(finalize(seg))
        run_type = seg["type"]
        start = seg
        energies = [cast("float", seg["energy_db"])]
        peaks = [cast("float", seg["peak_count"])]

    phases.append(finalize(segments[-1]))
    return phases


def _call_response(phases: list[dict[str, object]]) -> list[dict[str, object]]:
    """Detect adjacent solo<->chorus phase transitions as call-and-response patterns."""
    patterns: list[dict[str, object]] = []
    chorus_like = ("chorus", "ensemble")
    for a, b in pairwise(phases):
        if a["type"] == "solo" and b["type"] in chorus_like:
            pattern = "solo -> chorus (call and response)"
        elif a["type"] in chorus_like and b["type"] == "solo":
            pattern = "chorus -> solo (return to lead)"
        else:
            continue
        patterns.append(
            {
                "call_time": a["start"],
                "call_type": a["type"],
                "response_time": b["start"],
                "response_type": b["type"],
                "pattern": pattern,
            }
        )
    return patterns


def analyze(audio: Path, sr: int = 22050, window_sec: float = 3.0) -> dict[str, object]:
    """Segment the vocals into narrative phases and call-response patterns."""
    y, sr_loaded = librosa.load(str(audio), sr=sr, mono=True)
    sr = int(sr_loaded)
    duration = float(librosa.get_duration(y=y, sr=sr))

    window_samples = int(window_sec * sr)
    hop_samples = max(1, int(window_sec * sr / 2))  # 50% overlap

    segments: list[dict[str, object]] = []
    pos = 0
    while pos + window_samples <= len(y):
        t_center = (pos + window_samples / 2) / sr
        segments.append(_analyze_segment(y[pos : pos + window_samples], sr, t_center))
        pos += hop_samples

    phases = _build_phases(segments)
    call_response = _call_response(phases)

    type_durations: dict[str, float] = {}
    for phase in phases:
        ptype = cast("str", phase["type"])
        type_durations[ptype] = type_durations.get(ptype, 0.0) + cast("float", phase["duration_s"])
    total_dur = sum(type_durations.values())
    type_pcts = (
        {t: round(d / total_dur * 100, 1) for t, d in type_durations.items()}
        if total_dur > 0
        else {}
    )

    results: dict[str, object] = {
        "duration": round(duration, 2),
        "total_phases": len(phases),
        "total_call_response": len(call_response),
        "type_distribution": type_pcts,
        "phases": phases,
        "call_response_patterns": call_response[:20],
        "segments": segments,
    }
    return cast("dict[str, object]", sanitize(results))
