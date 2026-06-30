"""Depth / reverb analysis — RT60, pre-delay, wetness and perceived distance."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import librosa
import numpy as np
import numpy.typing as npt

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path

_SAMPLE_RATE = 22050
_HOP = 512
_N_FFT = 2048


def _room_label(rt60: float) -> tuple[str, str]:
    """Return (room_size, perceived_distance) from RT60 in seconds."""
    if rt60 > 1.5:
        return "cathedral / large hall", "far - across the room"
    if rt60 > 0.8:
        return "concert hall / large studio", "moderate - middle of room"
    if rt60 > 0.4:
        return "medium room / studio", "near - close mic with room"
    if rt60 > 0.15:
        return "small room / vocal booth", "intimate - close to ear"
    return "dry / close-mic / no room", "in your ear"


def _spatial_placement(pre_delay_ms: float) -> str:
    if pre_delay_ms > 40:
        return "source is far from reflective surfaces"
    if pre_delay_ms > 20:
        return "source is moderately placed in room"
    if pre_delay_ms > 5:
        return "source is close to reflective surface"
    return "direct / no early reflections"


def _decay_analysis(y: npt.NDArray[np.float64], sr: int) -> tuple[list[float], list[float]]:
    """Sample up to 30 onsets; return (rt60_list, pre_delay_list)."""
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True)
    kernel = np.ones(256) / 256
    decay_times: list[float] = []
    pre_delays: list[float] = []

    for onset_frame in onset_frames[:30]:
        start_sample = int(onset_frame) * _HOP
        window = y[start_sample : start_sample + sr * 2]
        if len(window) < sr or len(window) <= 256:
            continue

        envelope = np.abs(window)
        envelope_smooth = np.convolve(envelope, kernel, mode="same")

        peak_idx = int(np.argmax(envelope_smooth[: sr // 2]))
        peak_val = float(envelope_smooth[peak_idx])
        if peak_val < 0.01:
            continue

        pre_delay_sec = peak_idx / sr
        if 0.001 < pre_delay_sec < 0.1:
            pre_delays.append(pre_delay_sec)

        threshold = peak_val * 0.001
        decay_idx: int | None = None
        for i in range(peak_idx, len(envelope_smooth)):
            if envelope_smooth[i] < threshold:
                decay_idx = i
                break

        if decay_idx is not None:
            rt60 = (decay_idx - peak_idx) / sr
            if 0.05 < rt60 < 5.0:
                decay_times.append(rt60)

    return decay_times, pre_delays


def _spectral_persistence(s: npt.NDArray[np.float64]) -> float:
    """Mean autocorrelation persistence at lag=3 across 20-bin spectral bands."""
    values: list[float] = []
    for band_start in range(0, s.shape[0], 20):
        band = s[band_start : band_start + 20, :]
        band_energy = band.mean(axis=0)
        if len(band_energy) <= 10 or float(np.std(band_energy)) <= 0:
            continue
        band_norm = (band_energy - np.mean(band_energy)) / (np.std(band_energy) + 1e-10)
        autocorr = np.correlate(band_norm[:500], band_norm[:500], mode="full")
        autocorr = autocorr[len(autocorr) // 2 :]
        if len(autocorr) > 5 and float(autocorr[0]) > 0:
            values.append(max(0.0, float(autocorr[3]) / float(autocorr[0])))
    return float(np.mean(values)) if values else 0.0


def analyze(audio: Path) -> dict[str, object]:
    """Estimate RT60, pre-delay, wetness and perceived distance of the source mix."""
    y, sr_raw = librosa.load(str(audio), sr=_SAMPLE_RATE, mono=True)
    sr = int(sr_raw)

    duration = float(librosa.get_duration(y=y, sr=sr))
    result: dict[str, object] = {"duration": round(duration, 2)}

    decay_times, pre_delays = _decay_analysis(y, sr)

    if decay_times:
        result["rt60_estimate"] = round(float(np.median(decay_times)), 4)
        result["rt60_std"] = round(float(np.std(decay_times)), 4)
    else:
        result["rt60_estimate"] = 0.0

    result["pre_delay_ms"] = round(float(np.median(pre_delays)) * 1000, 2) if pre_delays else 0.0

    s = np.abs(librosa.stft(y, n_fft=_N_FFT, hop_length=_HOP)).astype(np.float64)
    result["spectral_persistence"] = round(_spectral_persistence(s), 4)

    flatness = librosa.feature.spectral_flatness(y=y)[0]
    result["spectral_flatness_mean"] = round(float(np.mean(flatness)), 4)
    result["spectral_flatness_std"] = round(float(np.std(flatness)), 4)

    # defensive coercion — keys may hold None after sanitize on a prior run
    rt60 = float(cast("float", result.get("rt60_estimate")) or 0)
    persistence = float(cast("float", result.get("spectral_persistence")) or 0)
    flatness_mean = float(cast("float", result.get("spectral_flatness_mean")) or 0)
    wetness = persistence * 0.5 + flatness_mean * 5.0 + min(rt60, 2.0) * 0.3
    result["wetness_index"] = round(float(min(wetness, 1.0)), 4)

    room, distance = _room_label(rt60)
    result["room_size"] = room
    result["perceived_distance"] = distance

    pre_delay_ms = float(cast("float", result.get("pre_delay_ms")) or 0)
    result["spatial_placement"] = _spatial_placement(pre_delay_ms)

    return cast("dict[str, object]", sanitize(result))
