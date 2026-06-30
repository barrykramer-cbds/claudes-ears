"""stereo_field.analyze: output contract, mono degraded path, ISSUE-004 NaN guard."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import numpy as np

from claudes_ears.analysis import stereo_field

if TYPE_CHECKING:
    import pytest

_SR = 22050
_REQUIRED_KEYS = {
    "stereo",
    "duration",
    "stereo_width",
    "mid_pct",
    "side_pct",
    "lr_balance",
    "balance_desc",
    "lr_correlation",
    "correlation_desc",
    "band_width",
    "widest_band",
    "narrowest_band",
    "width_timeline",
    "stereo_events",
}


def _stereo_samples(n: int = _SR * 4) -> np.ndarray:
    """Simple stereo signal: left sine, right cosine."""
    t = np.linspace(0, 1, n, dtype=np.float64)
    left = np.sin(2 * np.pi * 440 * t)
    right = np.cos(2 * np.pi * 440 * t)
    return np.stack([left, right])


def _patch_librosa_stereo(monkeypatch: pytest.MonkeyPatch, samples: np.ndarray) -> None:
    n_fft = 2048
    hop = 512
    freqs = np.linspace(0, _SR / 2, n_fft // 2 + 1)
    n_frames = samples.shape[1] // hop + 1
    fake_stft = np.ones((n_fft // 2 + 1, n_frames), dtype=np.float64) * 0.1

    fake = SimpleNamespace(
        load=lambda *a, **k: (samples, _SR),
        get_duration=lambda **k: samples.shape[1] / _SR,
        stft=lambda ch, **k: fake_stft,
        fft_frequencies=lambda **k: freqs,
    )
    monkeypatch.setattr(stereo_field, "librosa", fake)


def _patch_librosa_mono(monkeypatch: pytest.MonkeyPatch) -> None:
    mono = np.ones(_SR * 2, dtype=np.float64) * 0.5
    fake = SimpleNamespace(
        load=lambda *a, **k: (mono, _SR),
        get_duration=lambda **k: len(mono) / _SR,
    )
    monkeypatch.setattr(stereo_field, "librosa", fake)


def test_stereo_emits_full_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_librosa_stereo(monkeypatch, _stereo_samples())
    result = stereo_field.analyze(Path("song.mp3"))
    assert set(result) >= _REQUIRED_KEYS
    assert result["stereo"] is True
    assert isinstance(result["duration"], float)
    assert isinstance(result["band_width"], dict)


def test_stereo_width_timeline_populated(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_librosa_stereo(monkeypatch, _stereo_samples(_SR * 10))
    result = stereo_field.analyze(Path("song.mp3"))
    assert isinstance(result["width_timeline"], list)


def test_mono_source_returns_degraded_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_librosa_mono(monkeypatch)
    result = stereo_field.analyze(Path("mono.wav"))
    assert set(result) >= _REQUIRED_KEYS
    assert result["stereo"] is False
    assert result["stereo_width"] is None
    assert result["lr_correlation"] is None
    assert result["correlation_desc"] is None
    assert result["width_timeline"] == []
    assert result["stereo_events"] == []


def test_zero_variance_channel_yields_none_correlation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ISSUE-004: one silent channel has zero variance — corrcoef would return NaN
    silent_right = np.zeros(_SR * 2, dtype=np.float64)
    active_left = np.sin(np.linspace(0, 2 * np.pi * 440, _SR * 2))
    samples = np.stack([active_left, silent_right])
    _patch_librosa_stereo(monkeypatch, samples)
    result = stereo_field.analyze(Path("song.mp3"))
    assert result["stereo"] is True
    # must be None (not NaN), so sanitize can pass it through cleanly
    assert result["lr_correlation"] is None
    assert result["correlation_desc"] is None


def test_correlation_desc_maps_correctly() -> None:
    assert stereo_field._correlation_desc(0.97) == "near-mono (L~=R)"
    assert stereo_field._correlation_desc(0.85) == "centered with width"
    assert stereo_field._correlation_desc(0.6) == "wide stereo field"
    assert stereo_field._correlation_desc(0.2) == "very wide / spatial effects"
    assert stereo_field._correlation_desc(-0.1) == "phase effects present"
    assert stereo_field._correlation_desc(None) is None


def test_no_nan_in_result(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_librosa_stereo(monkeypatch, _stereo_samples())
    result = stereo_field.analyze(Path("song.mp3"))

    def _has_nan(obj: object) -> bool:
        if isinstance(obj, float):
            import math

            return not math.isfinite(obj)
        if isinstance(obj, dict):
            return any(_has_nan(v) for v in obj.values())
        if isinstance(obj, list):
            return any(_has_nan(v) for v in obj)
        return False

    assert not _has_nan(result), "Result must contain no NaN/inf values"
