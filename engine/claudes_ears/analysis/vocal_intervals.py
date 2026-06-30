"""Vocal harmonic-interval profiling — pitch relationships between simultaneous lines."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import numpy as np

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from numpy.typing import NDArray

_SR = 22050
_HOP = 512
_N_BINS = 60
_BINS_PER_OCTAVE = 12
_FRAME_FLOOR = 0.01
_PEAK_THRESHOLD = 0.3
_SAMPLE_EVERY = 10
_MAX_SAMPLES = 200

INTERVAL_NAMES: dict[int, tuple[str, str]] = {
    0: ("unison", "unity / reinforcement"),
    1: ("minor 2nd", "tension / dissonance / rub"),
    2: ("major 2nd", "mild tension / passing"),
    3: ("minor 3rd", "dark sweetness / melancholy"),
    4: ("major 3rd", "bright sweetness / joy"),
    5: ("perfect 4th", "openness / suspension"),
    6: ("tritone", "maximum tension / the devil's interval"),
    7: ("perfect 5th", "power / strength / medieval"),
    8: ("minor 6th", "yearning / bittersweet"),
    9: ("major 6th", "warmth / golden ratio interval"),
    10: ("minor 7th", "blues / funk / unresolved"),
    11: ("major 7th", "reaching / almost-octave tension"),
    12: ("octave", "power doubling / fullness"),
}

_CONSONANT = (0, 3, 4, 5, 7, 8, 9, 12)


def _interval_class(semitones: int) -> int:
    """Reduce to one octave but keep a true octave (a nonzero multiple of 12) as 12, not 0."""
    reduced = semitones % 12
    return 12 if reduced == 0 and semitones >= 12 else reduced


def _find_peaks(frame_norm: NDArray[np.floating]) -> list[int]:
    """Return local-maximum bin indices above the peak threshold."""
    peaks: list[int] = []
    for i in range(1, len(frame_norm) - 1):
        if (
            frame_norm[i] > _PEAK_THRESHOLD
            and frame_norm[i] > frame_norm[i - 1]
            and frame_norm[i] > frame_norm[i + 1]
        ):
            peaks.append(i)
    return peaks


def _character(counts: Mapping[int, int], total: int) -> str:
    """Name the harmonic palette from the interval distribution."""
    if total == 0:
        return "insufficient harmonic data"
    sweet = counts[3] + counts[4]
    power = counts[7] + counts[0] + counts[12]
    tension = counts[1] + counts[6] + counts[11]
    if sweet > power and sweet > tension:
        return "sweet harmonies (thirds dominant)"
    if power > sweet and power > tension:
        return "power harmonies (fifths/unisons dominant)"
    if tension > sweet and tension > power:
        return "tense harmonies (dissonance dominant)"
    return "balanced harmonic palette"


def _profile(cqt: NDArray[np.floating], sr: int, duration: float) -> dict[str, object]:
    """Build the interval profile from a magnitude CQT matrix (bins x frames)."""
    counts: dict[int, int] = dict.fromkeys(range(13), 0)
    samples: list[dict[str, float | int]] = []

    for frame_idx in range(cqt.shape[1]):
        frame = cqt[:, frame_idx]
        peak = float(frame.max())
        if peak < _FRAME_FLOOR:
            continue
        peaks = _find_peaks(frame / peak)
        if len(peaks) < 2:
            continue
        for i in range(len(peaks)):
            for j in range(i + 1, len(peaks)):
                semitones = abs(peaks[j] - peaks[i])
                interval = _interval_class(semitones)
                counts[interval] += 1
                if frame_idx % _SAMPLE_EVERY == 0:
                    samples.append(
                        {
                            "time": round(frame_idx * _HOP / sr, 2),
                            "interval": interval,
                            "semitones_raw": semitones,
                        }
                    )

    total = sum(counts.values())
    profile = sorted(
        (
            {
                "semitones": semitones,
                "name": INTERVAL_NAMES[semitones][0],
                "meaning": INTERVAL_NAMES[semitones][1],
                "count": counts[semitones],
                "pct": round(counts[semitones] / total * 100, 2) if total else 0.0,
            }
            for semitones in range(13)
        ),
        key=lambda entry: cast("int", entry["count"]),
        reverse=True,
    )
    consonance_ratio = round(sum(counts[i] for i in _CONSONANT) / total, 4) if total else 0.0

    result: dict[str, object] = {
        "duration": round(duration, 2),
        "total_interval_events": total,
        "consonance_ratio": consonance_ratio,
        "harmonic_character": _character(counts, total),
        "interval_profile": profile,
        "sample_intervals": samples[:_MAX_SAMPLES],
    }
    if total:
        dom = profile[0]
        result["dominant_interval"] = {
            "name": dom["name"],
            "meaning": dom["meaning"],
            "pct": dom["pct"],
        }
    return cast("dict[str, object]", sanitize(result))


def analyze(audio: Path) -> dict[str, object]:
    """Profile melodic/harmonic intervals and consonance in the vocals stem."""
    import librosa  # deferred: the ml extra is absent in the contract/test env

    y, sr = librosa.load(str(audio), sr=_SR, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))
    cqt = np.abs(
        librosa.cqt(
            y,
            sr=sr,
            hop_length=_HOP,
            fmin=librosa.note_to_hz("C2"),
            n_bins=_N_BINS,
            bins_per_octave=_BINS_PER_OCTAVE,
        )
    )
    return _profile(cqt, int(sr), duration)
