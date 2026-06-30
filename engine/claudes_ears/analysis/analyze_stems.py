"""Per-stem feature extraction feeding the 12-dim genome vector (schema §3)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import librosa
import numpy as np
from numpy.typing import NDArray

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_Signal = NDArray[np.float32]

_SAMPLE_RATE = 22050
_PITCH_CLASSES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_STEM_EXTENSIONS = (".wav", ".mp3")


def _load(path: Path) -> tuple[_Signal, int]:
    y, sr = librosa.load(path, sr=_SAMPLE_RATE, mono=True)
    return y, int(sr)


def _melodic_entropy(voiced_f0: _Signal) -> float:
    midi = np.round(librosa.hz_to_midi(voiced_f0)).astype(int)
    transitions = np.zeros((12, 12))
    for i in range(len(midi) - 1):
        transitions[midi[i] % 12, midi[i + 1] % 12] += 1
    row_sums = transitions.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    probs = transitions / row_sums
    entropies = [
        float(-np.sum(row[row > 0] * np.log2(row[row > 0]))) for row in probs if (row > 0).any()
    ]
    return round(float(np.mean(entropies)), 4) if entropies else 0.0


def _analyze_vocals(y: _Signal, sr: int) -> dict[str, object]:
    results: dict[str, object] = {
        "stem": "vocals",
        "duration": round(float(librosa.get_duration(y=y, sr=sr)), 2),
    }
    f0, _voiced, _vprob = librosa.pyin(
        y, fmin=float(librosa.note_to_hz("C2")), fmax=float(librosa.note_to_hz("C6")), sr=sr
    )
    voiced_f0 = f0[~np.isnan(f0)]
    if len(voiced_f0) > 10:
        results["pitch_mean_hz"] = round(float(np.mean(voiced_f0)), 1)
        results["pitch_range_semitones"] = round(float(np.ptp(librosa.hz_to_midi(voiced_f0))), 1)
        results["voiced_fraction"] = round(float(np.mean(~np.isnan(f0))), 3)
        results["vocal_melodic_entropy"] = _melodic_entropy(voiced_f0)

    flatness = librosa.feature.spectral_flatness(y=y)[0]
    mean_flatness = float(np.mean(flatness))
    results["breathiness"] = round(mean_flatness, 4)
    results["breathiness_desc"] = (
        "airy" if mean_flatness > 0.1 else "clear" if mean_flatness > 0.01 else "pure"
    )

    rms_db = librosa.amplitude_to_db(librosa.feature.rms(y=y)[0], ref=np.max)
    good = rms_db[rms_db > -60]
    results["dynamic_range_db"] = round(float(np.ptp(good)), 1) if len(good) else 0.0
    return results


def _band_energy(spectrum: _Signal, freqs: _Signal, low: float, high: float | None) -> float:
    mask = freqs >= low
    if high is not None:
        mask = mask & (freqs <= high)
    return float(np.mean(spectrum[mask, :])) if mask.any() else 0.0


def _kit_balance(y: _Signal, sr: int) -> dict[str, float]:
    spectrum = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    kick = _band_energy(spectrum, freqs, 20.0, 150.0)
    snare = _band_energy(spectrum, freqs, 150.0, 1000.0)
    hihat = _band_energy(spectrum, freqs, 5000.0, None)
    total = kick + snare + hihat + 1e-10
    return {
        "kick": round(kick / total * 100, 1),
        "snare": round(snare / total * 100, 1),
        "hihat": round(hihat / total * 100, 1),
    }


def _analyze_drums(y: _Signal, sr: int) -> dict[str, object]:
    duration = float(librosa.get_duration(y=y, sr=sr))
    results: dict[str, object] = {"stem": "drums", "duration": round(duration, 2)}

    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    results["tempo_bpm"] = round(float(np.atleast_1d(tempo)[0]), 1)
    beat_times = librosa.frames_to_time(beats, sr=sr)
    if len(beat_times) > 2:
        intervals = np.diff(beat_times)
        results["beat_regularity"] = round(1.0 - float(np.std(intervals) / np.mean(intervals)), 4)

    onset_times = librosa.frames_to_time(librosa.onset.onset_detect(y=y, sr=sr), sr=sr)
    results["onsets_per_second"] = round(len(onset_times) / max(duration, 1.0), 2)
    results["kit_balance"] = _kit_balance(y, sr)
    return results


def _analyze_bass(y: _Signal, sr: int) -> dict[str, object]:
    results: dict[str, object] = {
        "stem": "bass",
        "duration": round(float(librosa.get_duration(y=y, sr=sr)), 2),
    }
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)
    results["dominant_notes"] = [_PITCH_CLASSES[int(i)] for i in np.argsort(chroma_mean)[::-1][:4]]

    dominant = np.argmax(chroma, axis=0)
    changes = int(np.sum(np.diff(dominant) != 0))
    rate = changes / max(len(dominant), 1)
    results["root_movement_rate"] = round(rate, 4)
    results["root_movement_desc"] = (
        "highly active" if rate > 0.3 else "moderate" if rate > 0.15 else "anchored"
    )
    return results


def _texture(centroid: float, bandwidth: float, flatness: float) -> str:
    if flatness > 0.1:
        return "noisy / distorted"
    if centroid > 4000:
        return "bright / shimmering"
    if centroid < 1500:
        return "dark / warm pads"
    if bandwidth > 3000:
        return "wide / full"
    return "focused / midrange"


def _analyze_other(y: _Signal, sr: int) -> dict[str, object]:
    results: dict[str, object] = {
        "stem": "other",
        "duration": round(float(librosa.get_duration(y=y, sr=sr)), 2),
    }
    centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))
    bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]))
    flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)[0]))
    results["centroid_hz"] = round(centroid, 1)
    results["bandwidth_hz"] = round(bandwidth, 1)
    results["texture"] = _texture(centroid, bandwidth, flatness)

    harmonic, percussive = librosa.effects.hpss(y)
    harmonic_energy = float(np.sum(harmonic**2))
    percussive_energy = float(np.sum(percussive**2))
    total = harmonic_energy + percussive_energy + 1e-10
    results["harmonic_pct"] = round(harmonic_energy / total * 100, 1)

    onset_std = float(np.std(librosa.onset.onset_strength(y=y, sr=sr)))
    results["attack"] = (
        "rhythmic" if onset_std > 3 else "moderate" if onset_std > 1.5 else "sustained / pad-like"
    )
    return results


_ANALYZERS: dict[str, Callable[[_Signal, int], dict[str, object]]] = {
    "vocals": _analyze_vocals,
    "drums": _analyze_drums,
    "bass": _analyze_bass,
    "other": _analyze_other,
}


def _find_stem(stem_dir: Path, name: str) -> Path | None:
    for ext in _STEM_EXTENSIONS:
        candidate = stem_dir / f"{name}{ext}"
        if candidate.is_file():
            return candidate
    return None


def analyze(stem_dir: Path) -> dict[str, object]:
    """Per-stem features for whichever of the four demucs stems exist in ``stem_dir``."""
    results: dict[str, object] = {}
    for name, analyzer in _ANALYZERS.items():
        stem_path = _find_stem(stem_dir, name)
        if stem_path is None:
            continue
        y, sr = _load(stem_path)
        results[name] = analyzer(y, sr)
    return cast("dict[str, object]", sanitize(results))
