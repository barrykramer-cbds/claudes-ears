"""Per-band spectral overlap, competition, and territory between stem pairs."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import numpy as np
import numpy.typing as npt

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path

_SR = 22050
_N_FFT = 2048
_STEM_NAMES = ("vocals", "drums", "bass", "other")
_EXTS = (".wav", ".mp3")
_EPS = 1e-10

FloatArray = npt.NDArray[np.float64]


def _load_stems(stem_dir: Path) -> dict[str, FloatArray]:
    import librosa  # ml-extra dep; imported lazily so the contract loads without it

    stems: dict[str, FloatArray] = {}
    for name in _STEM_NAMES:
        for ext in _EXTS:
            path = stem_dir / f"{name}{ext}"
            if path.exists():
                audio, _ = librosa.load(path, sr=_SR, mono=True)
                stems[name] = np.asarray(audio, dtype=np.float64)
                break
    return stems


def _bands() -> dict[str, tuple[int, int]]:
    return {
        "sub_bass": (20, 80),
        "bass": (80, 300),
        "low_mid": (300, 800),
        "mid": (800, 2000),
        "upper_mid": (2000, 5000),
        "presence": (5000, 8000),
        "air": (8000, _SR // 2),
    }


def _spectrograms(stems: dict[str, FloatArray]) -> dict[str, FloatArray]:
    import librosa

    min_len = min(len(y) for y in stems.values())
    return {
        name: np.abs(librosa.stft(y[:min_len], n_fft=_N_FFT)).astype(np.float64)
        for name, y in stems.items()
    }


def _band_metrics(band_a: FloatArray, band_b: FloatArray) -> tuple[float, float, float, float]:
    overlap = float(np.sum(np.minimum(band_a, band_b)))
    combined = float(np.sum(band_a) + np.sum(band_b)) + _EPS
    overlap_ratio = overlap / (combined / 2)

    if np.std(band_a) > 0 and np.std(band_b) > 0:
        correlation = float(np.corrcoef(band_a, band_b)[0, 1])
    else:
        correlation = 0.0

    e_a, e_b = float(np.mean(band_a)), float(np.mean(band_b))
    dominance = (e_a - e_b) / (e_a + e_b) if e_a + e_b > 0 else 0.0
    return overlap_ratio, correlation, dominance, combined


def _pair_data(
    name_a: str,
    name_b: str,
    spec_a: FloatArray,
    spec_b: FloatArray,
    freqs: FloatArray,
    bands: dict[str, tuple[int, int]],
) -> dict[str, object]:
    band_results: dict[str, object] = {}
    total_overlap = 0.0
    total_energy = 0.0

    for band_name, (lo, hi) in bands.items():
        mask = (freqs >= lo) & (freqs < hi)
        if not mask.any():
            continue

        band_a = spec_a[mask, :].mean(axis=0)
        band_b = spec_b[mask, :].mean(axis=0)
        overlap_ratio, correlation, dominance, combined = _band_metrics(band_a, band_b)

        band_results[band_name] = {
            "overlap": round(overlap_ratio, 4),
            "correlation": round(correlation, 4),
            "dominance": round(dominance, 4),
            "dominant": name_a if dominance > 0.1 else name_b if dominance < -0.1 else "shared",
        }
        total_overlap += float(np.sum(np.minimum(band_a, band_b)))
        total_energy += combined

    high_overlap = [
        b for b, d in band_results.items() if isinstance(d, dict) and float(d["overlap"]) > 0.3
    ]
    return {
        "pair": f"{name_a} vs {name_b}",
        "bands": band_results,
        "overall_overlap": round(total_overlap / (total_energy / 2 + _EPS), 4),
        "competition": (
            f"competing in: {', '.join(high_overlap)}" if high_overlap else "well separated"
        ),
    }


def _territory(
    specs: dict[str, FloatArray], freqs: FloatArray, bands: dict[str, tuple[int, int]]
) -> dict[str, dict[str, float]]:
    territory: dict[str, dict[str, float]] = {}
    for band_name, (lo, hi) in bands.items():
        mask = (freqs >= lo) & (freqs < hi)
        if not mask.any():
            continue
        energies = {name: float(np.mean(spec[mask, :])) for name, spec in specs.items()}
        total = sum(energies.values()) + _EPS
        territory[band_name] = {
            name: round(energy / total * 100, 1)
            for name, energy in sorted(energies.items(), key=lambda kv: -kv[1])
        }
    return territory


def analyze(stem_dir: Path) -> dict[str, object]:
    """Compute per-band overlap/competition across the separated stems."""
    stems = _load_stems(stem_dir)

    # Pairwise interaction is undefined with fewer than two stems.
    if len(stems) < 2:
        empty: dict[str, object] = {"stem_count": len(stems), "pairs": [], "territory": {}}
        return cast("dict[str, object]", sanitize(empty))

    import librosa

    specs = _spectrograms(stems)
    freqs = np.asarray(librosa.fft_frequencies(sr=_SR, n_fft=_N_FFT), dtype=np.float64)
    bands = _bands()

    names = list(specs.keys())
    pairs = [
        _pair_data(names[i], names[j], specs[names[i]], specs[names[j]], freqs, bands)
        for i in range(len(names))
        for j in range(i + 1, len(names))
    ]

    result = {
        "stem_count": len(stems),
        "pairs": pairs,
        "territory": _territory(specs, freqs, bands),
    }
    return cast("dict[str, object]", sanitize(result))
