"""Behavioral tests for register_tracking — variant moment shapes, unrounded f0, degraded input."""

from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from claudes_ears.analysis import register_tracking
from claudes_ears.analysis.register_tracking import analyze, detect_register

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def fake_librosa(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Replace register_tracking's librosa global so tests never touch the real DSP stack.

    Returns an installer taking (y, f0, sr); the real librosa is unusable here
    (numba rejects numpy 2.5), so the whole namespace is swapped out.
    """

    def install(y: np.ndarray, f0: np.ndarray, sr: int = 22050) -> None:
        nbins = register_tracking._N_FFT // 2 + 1
        fake = SimpleNamespace(
            load=lambda *a, **k: (y, sr),
            get_duration=lambda *a, **k: len(y) / sr,
            pyin=lambda *a, **k: (f0, None, None),
            fft_frequencies=lambda *a, **k: np.linspace(0, sr / 2, nbins),
            stft=lambda seg, **k: np.abs(np.fft.rfft(seg, n=register_tracking._N_FFT))[:, None],
            effects=SimpleNamespace(harmonic=lambda seg: seg),
        )
        monkeypatch.setattr(register_tracking, "librosa", fake)

    return install


@pytest.fixture
def chest_then_falsetto() -> tuple[np.ndarray, np.ndarray]:
    """Six seconds: a low tone, then a tone well above the median (a register lift)."""
    sr = 22050
    t = np.arange(sr * 6) / sr
    low = (np.sin(2 * np.pi * 150 * t[: sr * 3]) * 0.3).astype(np.float32)
    high = (np.sin(2 * np.pi * 600 * t[sr * 3 :]) * 0.3).astype(np.float32)
    y = np.concatenate([low, high])

    frames = len(y) // register_tracking._HOP + 1
    f0 = np.empty(frames, dtype=np.float64)
    half = frames // 2
    f0[:half] = 150.123456
    f0[half:] = 600.654321
    return y, f0


def test_returns_canonical_top_level_keys(
    fake_librosa: Callable[..., None], chest_then_falsetto: tuple[np.ndarray, np.ndarray]
) -> None:
    fake_librosa(*chest_then_falsetto)
    out = analyze(Path("vocals.wav"))

    assert set(out) >= {
        "duration",
        "singer_median_f0",
        "singer_range_low",
        "singer_range_high",
        "total_register_phases",
        "total_transitions",
        "register_distribution",
        "phases",
        "transitions",
        "moments",
    }


def test_singer_f0_fields_are_unrounded(
    fake_librosa: Callable[..., None], chest_then_falsetto: tuple[np.ndarray, np.ndarray]
) -> None:
    fake_librosa(*chest_then_falsetto)
    out = analyze(Path("vocals.wav"))

    median = out["singer_median_f0"]
    assert isinstance(median, float)
    assert median != round(median, 1)


def test_moments_have_variant_shape(
    fake_librosa: Callable[..., None], chest_then_falsetto: tuple[np.ndarray, np.ndarray]
) -> None:
    fake_librosa(*chest_then_falsetto)
    out = analyze(Path("vocals.wav"))

    moments = out["moments"]
    assert isinstance(moments, list)
    base = {"time", "label", "register", "confidence", "f0", "energy_db"}
    spectral = {"spectral_slope", "harmonic_ratio"}
    for m in moments:
        assert base <= set(m)
        if m["register"] == "silence":
            assert not (spectral & set(m))
        else:
            assert spectral <= set(m)


def test_detects_register_transition(
    fake_librosa: Callable[..., None], chest_then_falsetto: tuple[np.ndarray, np.ndarray]
) -> None:
    fake_librosa(*chest_then_falsetto)
    out = analyze(Path("vocals.wav"))

    registers = {p["register"] for p in cast("list[dict[str, object]]", out["phases"])}
    assert len(registers - {"silence"}) >= 2
    assert cast("int", out["total_transitions"]) >= 1


def test_silent_input_yields_only_silence(fake_librosa: Callable[..., None]) -> None:
    sr = 22050
    y = np.zeros(sr * 4, dtype=np.float32)
    f0 = np.zeros(len(y) // register_tracking._HOP + 1)
    fake_librosa(y, f0)
    out = analyze(Path("vocals.wav"))

    assert out["total_register_phases"] == 0
    assert out["total_transitions"] == 0
    assert out["register_distribution"] == {}
    moments = cast("list[dict[str, object]]", out["moments"])
    assert all(m["register"] == "silence" for m in moments)


def test_empty_audio_is_handled(fake_librosa: Callable[..., None]) -> None:
    fake_librosa(np.zeros(0, dtype=np.float32), np.zeros(0))
    out = analyze(Path("vocals.wav"))

    assert out["moments"] == []
    assert out["phases"] == []
    assert out["singer_median_f0"] == register_tracking._FALLBACK_MEDIAN


def test_output_is_json_safe(
    fake_librosa: Callable[..., None], chest_then_falsetto: tuple[np.ndarray, np.ndarray]
) -> None:
    fake_librosa(*chest_then_falsetto)
    out = analyze(Path("vocals.wav"))

    for value in (out["singer_median_f0"], out["duration"]):
        assert value is None or math.isfinite(cast("float", value))


@pytest.mark.parametrize(
    ("f0", "slope", "energy_db", "expected"),
    [
        (0.0, -3.0, -10.0, "silence"),
        (120.0, -5.0, -55.0, "silence"),
        (150.0, -4.0, -10.0, "chest"),
        (300.0, -1.0, -12.0, "head"),
        (600.0, 0.5, -12.0, "falsetto"),
    ],
)
def test_detect_register_classification(
    f0: float, slope: float, energy_db: float, expected: str
) -> None:
    register, confidence = detect_register(f0, slope, 0.7, energy_db, singer_median=300.0)
    assert register == expected
    assert 0.0 <= confidence <= 1.0
