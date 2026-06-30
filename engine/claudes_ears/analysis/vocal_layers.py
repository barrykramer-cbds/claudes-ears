"""Vocal layering + echo detection from the vocals stem."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import librosa
import numpy as np

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

_SR = 22050
_HOP = 512
_N_FFT = 2048
_VOCAL_LO_HZ = 200.0
_VOCAL_HI_HZ = 4000.0
_PEAK_REL_THRESHOLD = 0.15
_MIN_ECHO_FRAMES = 100
_ECHO_MIN_LAG = 10
_ECHO_MAX_LAG = 200
_ECHO_STRENGTH = 0.3


def _frame_peak_count(frame: NDArray[np.float64], rel_threshold: float) -> int:
    """Count spectral bumps in one frame; more bumps imply more simultaneous voices."""
    peak = float(frame.max())
    if peak <= 0.0:
        return 0
    threshold = peak * rel_threshold
    count = 0
    in_peak = False
    for value in frame:
        if value > threshold and not in_peak:
            count += 1
            in_peak = True
        elif value < threshold:
            in_peak = False
    return count


def _harmonic_peak_counts(
    magnitude: NDArray[np.float64], freqs: NDArray[np.float64]
) -> NDArray[np.int_]:
    """Per-frame spectral-peak counts within the vocal band."""
    band = (freqs >= _VOCAL_LO_HZ) & (freqs <= _VOCAL_HI_HZ)
    vocal_band = magnitude[band, :]
    counts = [
        _frame_peak_count(vocal_band[:, i], _PEAK_REL_THRESHOLD) for i in range(vocal_band.shape[1])
    ]
    return np.asarray(counts, dtype=np.int_)


def _voiced_peaks(
    peak_counts: NDArray[np.int_], voiced_mask: NDArray[np.bool_], n_f0: int
) -> list[int]:
    """Peak counts sampled at voiced f0 frames, aligned across differing frame rates."""
    if len(peak_counts) == 0:
        return []
    ratio = len(peak_counts) / max(n_f0, 1)
    out: list[int] = []
    for i in range(n_f0):
        idx = int(i * ratio)
        if voiced_mask[i] and idx < len(peak_counts):
            out.append(int(peak_counts[idx]))
    return out


def _layering_label(avg_peaks: float) -> str:
    """Map mean voiced peak count to a human layering description."""
    if avg_peaks > 10:
        return "heavily layered (multiple voices)"
    if avg_peaks > 7:
        return "doubled / harmonized"
    if avg_peaks > 4:
        return "solo with occasional doubling"
    return "solo voice"


def _detect_echoes(rms: NDArray[np.float64], sr: int) -> list[dict[str, float]] | None:
    """Echoes via RMS-envelope autocorrelation; None means too short to judge."""
    if len(rms) <= _MIN_ECHO_FRAMES:
        return None
    norm = (rms - float(np.mean(rms))) / (float(np.std(rms)) + 1e-10)
    autocorr = np.correlate(norm, norm, mode="full")
    autocorr = autocorr[len(autocorr) // 2 :]
    autocorr = autocorr / (float(autocorr[0]) + 1e-10)
    max_lag = min(_ECHO_MAX_LAG, len(autocorr))
    search = autocorr[_ECHO_MIN_LAG:max_lag]
    echoes: list[dict[str, float]] = []
    if len(search) <= 10:
        return echoes
    for i in range(1, len(search) - 1):
        here = float(search[i])
        if here > float(search[i - 1]) and here > float(search[i + 1]) and here > _ECHO_STRENGTH:
            delay_s = round((i + _ECHO_MIN_LAG) * _HOP / sr, 3)
            echoes.append({"delay_s": delay_s, "strength": round(here, 3)})
    return echoes


def _dense_regions(
    peak_counts: NDArray[np.int_], times: NDArray[np.float64]
) -> tuple[list[dict[str, float]], float]:
    """Contiguous spans denser than the 90th percentile, plus the layered-time fraction."""
    high = float(np.percentile(peak_counts, 90))
    dense = peak_counts > high
    regions: list[dict[str, float]] = []
    in_region = False
    start = 0
    for i in range(len(dense)):
        if dense[i] and not in_region:
            start = i
            in_region = True
        elif not dense[i] and in_region:
            if i - start > 3:
                end_idx = min(i, len(times) - 1)
                regions.append(
                    {
                        "start": round(float(times[start]), 2),
                        "end": round(float(times[end_idx]), 2),
                        "density": round(float(np.mean(peak_counts[start:i])), 1),
                    }
                )
            in_region = False
    pct = round(float(np.mean(dense)) * 100, 1)
    return regions[:10], pct


def _insufficient(duration: float) -> dict[str, object]:
    return {
        "duration": duration,
        "harmonic_peaks_mean": 0.0,
        "harmonic_peaks_p90": 0.0,
        "layering": "solo voice",
        "echo_detected": False,
        "echo_desc": "insufficient data",
    }


def analyze(audio: Path) -> dict[str, object]:
    """Detect harmonic layering and echo structure in the vocals stem."""
    y_raw, sr_raw = librosa.load(str(audio), sr=_SR, mono=True)
    y = np.asarray(y_raw, dtype=np.float64)
    sr = int(sr_raw)
    duration = round(float(librosa.get_duration(y=y, sr=sr)), 2)
    if y.size == 0:
        return cast("dict[str, object]", sanitize(_insufficient(duration)))

    fmin = float(librosa.note_to_hz("C2"))
    fmax = float(librosa.note_to_hz("C6"))
    f0 = np.asarray(librosa.pyin(y, fmin=fmin, fmax=fmax, sr=sr)[0], dtype=np.float64)
    voiced_mask = ~np.isnan(f0)

    magnitude = np.asarray(np.abs(librosa.stft(y, n_fft=_N_FFT)), dtype=np.float64)
    freqs = np.asarray(librosa.fft_frequencies(sr=sr, n_fft=_N_FFT), dtype=np.float64)
    peak_counts = _harmonic_peak_counts(magnitude, freqs)

    voiced_peaks = _voiced_peaks(peak_counts, voiced_mask, len(f0))
    avg_peaks = float(np.mean(voiced_peaks)) if voiced_peaks else 0.0
    p90_peaks = float(np.percentile(voiced_peaks, 90)) if voiced_peaks else 0.0

    result: dict[str, object] = {
        "duration": duration,
        "harmonic_peaks_mean": round(avg_peaks, 1),
        "harmonic_peaks_p90": round(p90_peaks, 1),
        "layering": _layering_label(avg_peaks),
    }

    rms = np.asarray(
        librosa.feature.rms(y=y, frame_length=_N_FFT, hop_length=_HOP)[0], dtype=np.float64
    )
    echoes = _detect_echoes(rms, sr)
    if echoes is None:
        result["echo_detected"] = False
        result["echo_desc"] = "insufficient data"
    else:
        result["echo_detected"] = len(echoes) > 0
        result["echo_count"] = len(echoes)
        result["echoes"] = echoes[:5]
        result["echo_desc"] = (
            f"{len(echoes)} echo(es), primary {echoes[0]['delay_s']:.2f}s" if echoes else "no echo"
        )

    if len(peak_counts) > 0:
        times = np.asarray(
            librosa.frames_to_time(range(len(peak_counts)), sr=sr, hop_length=_HOP),
            dtype=np.float64,
        )
        regions, pct = _dense_regions(peak_counts, times)
        result["dense_regions"] = regions
        result["layering_pct"] = pct

    return cast("dict[str, object]", sanitize(result))
