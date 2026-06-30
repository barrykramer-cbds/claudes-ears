"""NMF timbral decomposition: split a stem into instrumental voices (schema §timbral)."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, cast
import warnings

import librosa
import numpy as np
from sklearn.decomposition import NMF

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

_SR = 22050
_N_FFT = 2048
_HOP = 512
_DEFAULT_COMPONENTS = 4


class _Template(TypedDict):
    centroid_range: tuple[float, float]
    harmonic_min: float


INSTRUMENT_TEMPLATES: dict[str, _Template] = {
    "bass guitar / synth bass": {"centroid_range": (60, 300), "harmonic_min": 0.7},
    "electric guitar (clean)": {"centroid_range": (800, 2500), "harmonic_min": 0.6},
    "electric guitar (distorted)": {"centroid_range": (1500, 4000), "harmonic_min": 0.3},
    "acoustic guitar": {"centroid_range": (600, 2000), "harmonic_min": 0.7},
    "piano / keys": {"centroid_range": (400, 3000), "harmonic_min": 0.75},
    "synth pad": {"centroid_range": (300, 2000), "harmonic_min": 0.8},
    "synth lead": {"centroid_range": (1000, 5000), "harmonic_min": 0.6},
    "strings / orchestral": {"centroid_range": (300, 3500), "harmonic_min": 0.85},
    "brass": {"centroid_range": (500, 3000), "harmonic_min": 0.7},
    "woodwind / flute": {"centroid_range": (800, 4000), "harmonic_min": 0.8},
    "sitar / plucked string": {"centroid_range": (200, 5000), "harmonic_min": 0.5},
    "percussion / transient": {"centroid_range": (2000, 8000), "harmonic_min": 0.0},
    "ambient / noise / texture": {"centroid_range": (1000, 8000), "harmonic_min": 0.0},
    "choir / vocal texture": {"centroid_range": (300, 3000), "harmonic_min": 0.7},
}


def classify_component(
    centroid: float, harmonic_pct: float, attack_sharpness: float
) -> tuple[str, float]:
    """Match a spectral component to the best-scoring instrument template."""
    best_match = "unknown"
    best_score = 0.0
    for name, template in INSTRUMENT_TEMPLATES.items():
        score = 0.0
        lo, hi = template["centroid_range"]
        if lo <= centroid <= hi:
            mid = (lo + hi) / 2
            score += max(0.0, 1 - abs(centroid - mid) / (hi - lo)) * 3
        else:
            score -= min(abs(centroid - lo), abs(centroid - hi)) / 1000
        if harmonic_pct / 100 >= template["harmonic_min"]:
            score += 2
        else:
            score -= 1
        if "percussion" in name or "transient" in name:
            if attack_sharpness > 0.5:
                score += 2
        elif ("pad" in name or "strings" in name or "ambient" in name) and attack_sharpness < 0.3:
            score += 2
        if score > best_score:
            best_score = score
            best_match = name
    return best_match, round(best_score, 2)


def _bound_components(requested: int, spectrogram: NDArray[np.floating]) -> int:
    """Clamp NMF rank to the spectrogram dimensions — nndsvd needs k <= min(bins, frames)."""
    n_bins, n_frames = spectrogram.shape
    return max(1, min(requested, int(n_bins), int(n_frames)))


def _empty_result(duration: float) -> dict[str, object]:
    return {
        "duration": round(duration, 2),
        "n_components": 0,
        "reconstruction_error": None,
        "components": [],
    }


def _analyze_component(
    spectral_template: NDArray[np.floating],
    activation: NDArray[np.floating],
    freqs: NDArray[np.floating],
    sr: int,
) -> dict[str, object]:
    total = float(spectral_template.sum())
    if total > 0:
        weights = spectral_template / total
        centroid = float(np.sum(weights * freqs))
        bandwidth = (
            float(np.sqrt(np.sum(weights * (freqs - centroid) ** 2))) if centroid > 0 else 0.0
        )
    else:
        centroid = 0.0
        bandwidth = 0.0

    template_norm = spectral_template / (spectral_template.max() + 1e-10)
    peaks = [
        j
        for j in range(1, len(template_norm) - 1)
        if template_norm[j] > 0.2
        and template_norm[j] > template_norm[j - 1]
        and template_norm[j] > template_norm[j + 1]
    ]
    if len(peaks) >= 2:
        ratios = [freqs[peaks[k]] / (freqs[peaks[0]] + 1e-10) for k in range(1, min(5, len(peaks)))]
        harmonic = [r for r in ratios if any(abs(r - n) < 0.15 for n in range(1, 8))]
        harmonic_pct = len(harmonic) / max(1, len(ratios)) * 100
    else:
        harmonic_pct = 50.0

    activation_diff = np.diff(activation)
    mean_activation = float(np.mean(activation)) + 1e-10
    if activation_diff.size > 0:
        peak_jump = float(np.percentile(np.abs(activation_diff), 95))
        attack_sharpness = min(1.0, peak_jump / mean_activation)
    else:
        attack_sharpness = 0.0

    peak_level = activation.max() + 1e-10
    active_pct = float(np.sum(activation > activation.max() * 0.1) / len(activation) * 100)
    energy = float(np.sum(activation**2))

    frame_times = librosa.frames_to_time(np.arange(len(activation)), sr=sr, hop_length=_HOP)
    peak_time = float(frame_times[np.argmax(activation)])

    n_points = min(100, len(activation))
    indices = np.linspace(0, len(activation) - 1, n_points, dtype=int)
    envelope = [
        {
            "time": round(float(frame_times[idx]), 2),
            "level": round(float(activation[idx] / peak_level), 4),
        }
        for idx in indices
    ]

    instrument, confidence = classify_component(centroid, harmonic_pct, attack_sharpness)
    top_indices = np.argsort(spectral_template)[-10:][::-1]
    top_freqs = [
        {
            "hz": round(float(freqs[idx]), 1),
            "weight": round(float(spectral_template[idx] / peak_level), 4),
        }
        for idx in top_indices
        if freqs[idx] > 0
    ]

    if attack_sharpness > 0.5:
        attack_type = "transient"
    elif attack_sharpness < 0.2:
        attack_type = "sustained"
    else:
        attack_type = "moderate"
    return {
        "centroid_hz": round(centroid, 1),
        "bandwidth_hz": round(bandwidth, 1),
        "harmonic_pct": round(harmonic_pct, 1),
        "attack_sharpness": round(attack_sharpness, 4),
        "attack_type": attack_type,
        "active_pct": round(active_pct, 1),
        "energy_contribution": round(energy, 2),
        "peak_time": round(peak_time, 2),
        "peak_time_label": f"{int(peak_time // 60)}:{int(peak_time % 60):02d}",
        "instrument_guess": instrument,
        "classification_confidence": confidence,
        "top_frequencies": top_freqs[:5],
        "activation_envelope": envelope,
    }


def analyze(audio: Path, n_components: int = _DEFAULT_COMPONENTS) -> dict[str, object]:
    """Decompose the 'other' stem into timbral components, bounding count to spectrogram size."""
    # Short 'other' stems legitimately trip n_fft and NMF-convergence warnings.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        y, _sr = librosa.load(str(audio), sr=_SR, mono=True)
        sr = int(_sr)
        duration = float(librosa.get_duration(y=y, sr=sr))
        if y.size == 0:
            return cast("dict[str, object]", sanitize(_empty_result(duration)))

        spectrogram = np.abs(librosa.stft(y, n_fft=_N_FFT, hop_length=_HOP))
        if spectrogram.shape[1] == 0:
            return cast("dict[str, object]", sanitize(_empty_result(duration)))

        bounded = _bound_components(n_components, spectrogram)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=_N_FFT)
        model = NMF(n_components=bounded, init="nndsvd", max_iter=300, random_state=42)
        w = model.fit_transform(spectrogram)  # freq bins x components
        h = model.components_  # components x frames

    components = [_analyze_component(w[:, i], h[i, :], freqs, sr) for i in range(bounded)]
    components.sort(key=lambda c: -cast("float", c["energy_contribution"]))
    total_energy = sum(cast("float", c["energy_contribution"]) for c in components) + 1e-10
    for rank, comp in enumerate(components, start=1):
        energy = cast("float", comp["energy_contribution"])
        comp["energy_pct"] = round(energy / total_energy * 100, 1)
        comp["rank"] = rank

    result = {
        "duration": round(duration, 2),
        "n_components": bounded,
        "reconstruction_error": round(float(model.reconstruction_err_), 2),
        "components": components,
    }
    return cast("dict[str, object]", sanitize(result))
