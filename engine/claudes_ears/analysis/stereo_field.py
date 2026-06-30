"""Stereo-field analysis — width, balance, correlation, and spectral band spread."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import librosa
import numpy as np
import numpy.typing as npt

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path

_SAMPLE_RATE = 22050
_N_FFT = 2048
_HOP = 512

_BANDS: dict[str, tuple[int, int]] = {
    "sub_bass (20-100)": (20, 100),
    "bass (100-300)": (100, 300),
    "low_mid (300-1000)": (300, 1000),
    "mid (1000-3000)": (1000, 3000),
    "upper_mid (3000-6000)": (3000, 6000),
    "high (6000+)": (6000, _SAMPLE_RATE // 2),
}


def _width_desc(width: float) -> str:
    if width > 0.8:
        return "very wide - instruments spread across field"
    if width > 0.4:
        return "moderately wide - clear L/R separation"
    if width > 0.15:
        return "moderate - mostly centered with some spread"
    return "narrow - nearly mono"


def _balance_desc(balance: float) -> str:
    if balance < -0.05:
        return "left-heavy"
    if balance > 0.05:
        return "right-heavy"
    return "balanced center"


def _correlation_desc(corr: float | None) -> str | None:
    if corr is None:
        return None
    if corr > 0.95:
        return "near-mono (L~=R)"
    if corr > 0.8:
        return "centered with width"
    if corr > 0.5:
        return "wide stereo field"
    if corr > 0:
        return "very wide / spatial effects"
    return "phase effects present"


def _mono_result(duration: float) -> dict[str, object]:
    """Degraded contract for a mono source — stereo metrics are undefined."""
    return {
        "stereo": False,
        "duration": round(duration, 2),
        "stereo_width": None,
        "mid_pct": None,
        "side_pct": None,
        "lr_balance": None,
        "balance_desc": None,
        "lr_correlation": None,
        "correlation_desc": None,
        "band_width": {},
        "widest_band": None,
        "narrowest_band": None,
        "width_timeline": [],
        "stereo_events": [],
    }


def _band_widths(
    s_left: npt.NDArray[np.float64],
    s_right: npt.NDArray[np.float64],
    freqs: npt.NDArray[np.float64],
) -> dict[str, float]:
    band_width: dict[str, float] = {}
    for name, (lo, hi) in _BANDS.items():
        mask = (freqs >= lo) & (freqs < hi)
        if mask.any():
            l_band = float(s_left[mask, :].mean())
            r_band = float(s_right[mask, :].mean())
            avg = (l_band + r_band) / 2 + 1e-10
            band_width[name] = round(abs(l_band - r_band) / avg, 4)
    return band_width


def _width_timeline(
    s_left: npt.NDArray[np.float64],
    s_right: npt.NDArray[np.float64],
    sr: int,
) -> list[dict[str, object]]:
    frame_count = min(s_left.shape[1], s_right.shape[1])
    window_frames = int(2 * sr / _HOP)
    timeline: list[dict[str, object]] = []
    for i in range(0, frame_count - window_frames, window_frames // 2):
        l_chunk = s_left[:, i : i + window_frames]
        r_chunk = s_right[:, i : i + window_frames]
        l_e = float(np.sum(l_chunk**2))
        r_e = float(np.sum(r_chunk**2))
        mid_e = float(np.sum(((l_chunk + r_chunk) / 2) ** 2))
        side_e = float(np.sum(((l_chunk - r_chunk) / 2) ** 2))
        timeline.append(
            {
                "time": round(i * _HOP / sr, 1),
                "width": round(side_e / (mid_e + 1e-10), 4),
                "balance": round((r_e - l_e) / (l_e + r_e + 1e-10), 4),
            }
        )
    return timeline


def analyze(audio: Path) -> dict[str, object]:
    """Measure width, balance and correlation of the source mix (mono-safe)."""
    y, sr_raw = librosa.load(str(audio), sr=_SAMPLE_RATE, mono=False)
    sr = int(sr_raw)

    # mono source — stereo metrics are undefined; return degraded shape
    if y.ndim == 1:
        duration = float(librosa.get_duration(y=y, sr=sr))
        return cast("dict[str, object]", sanitize(_mono_result(duration)))

    duration = y.shape[1] / sr
    left: npt.NDArray[np.float64] = y[0].astype(np.float64)
    right: npt.NDArray[np.float64] = y[1].astype(np.float64)

    mid = (left + right) / 2
    side = (left - right) / 2
    mid_energy = float(np.sum(mid**2))
    side_energy = float(np.sum(side**2))
    total = mid_energy + side_energy + 1e-10

    stereo_width = round(side_energy / (mid_energy + 1e-10), 4)

    left_energy = float(np.sum(left**2))
    right_energy = float(np.sum(right**2))
    balance = round((right_energy - left_energy) / (left_energy + right_energy + 1e-10), 4)

    # guard zero-variance before corrcoef — a silent/DC channel yields NaN otherwise
    min_len = min(len(left), len(right))
    l_slice, r_slice = left[:min_len], right[:min_len]
    if np.std(l_slice) > 0 and np.std(r_slice) > 0:
        correlation: float | None = round(float(np.corrcoef(l_slice, r_slice)[0, 1]), 4)
    else:
        correlation = None

    s_left = np.abs(librosa.stft(left, n_fft=_N_FFT)).astype(np.float64)
    s_right = np.abs(librosa.stft(right, n_fft=_N_FFT)).astype(np.float64)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=_N_FFT)

    band_width = _band_widths(s_left, s_right, freqs)
    widest = max(band_width, key=band_width.get) if band_width else None  # type: ignore[arg-type]
    narrowest = min(band_width, key=band_width.get) if band_width else None  # type: ignore[arg-type]

    timeline = _width_timeline(s_left, s_right, sr)

    stereo_events: list[dict[str, object]] = []
    if len(timeline) > 2:
        widths = [float(cast("float", w["width"])) for w in timeline]
        for i in range(1, len(widths)):
            delta = widths[i] - widths[i - 1]
            if abs(delta) > 0.1:
                stereo_events.append(
                    {
                        "time": timeline[i]["time"],
                        "type": "WIDEN" if delta > 0 else "NARROW",
                        "magnitude": round(abs(delta), 4),
                    }
                )
        stereo_events = stereo_events[:20]

    result: dict[str, object] = {
        "stereo": True,
        "duration": round(duration, 2),
        "stereo_width": stereo_width,
        "width_desc": _width_desc(stereo_width),
        "mid_pct": round(mid_energy / total * 100, 1),
        "side_pct": round(side_energy / total * 100, 1),
        "lr_balance": balance,
        "balance_desc": _balance_desc(balance),
        "lr_correlation": correlation,
        "correlation_desc": _correlation_desc(correlation),
        "band_width": band_width,
        "widest_band": widest,
        "narrowest_band": narrowest,
        "width_timeline": timeline,
        "stereo_events": stereo_events,
    }
    return cast("dict[str, object]", sanitize(result))
