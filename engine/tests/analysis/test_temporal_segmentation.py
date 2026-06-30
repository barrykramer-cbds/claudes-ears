"""temporal_segmentation.analyze: output contract, ISSUE-005 arc NaN guard."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import numpy as np

from claudes_ears.analysis import temporal_segmentation

if TYPE_CHECKING:
    import pytest

_SR = 22050
_WINDOW_SEC = 15
_HOP_SEC = 5

_REQUIRED_KEYS = {"snapshots", "narrative"}
_SNAPSHOT_KEYS = {
    "seg",
    "t_start",
    "t_end",
    "t_center",
    "time",
    "rms_mean",
    "rms_p90",
    "dyn_range",
    "centroid",
    "harm_pct",
    "key",
    "tension",
    "consonance",
    "warmth",
    "onset_density",
    "tempo",
}


def _make_segment_audio(n_windows: int) -> np.ndarray:
    """Produce exactly n_windows worth of audio at default window/hop."""
    total_samples = _WINDOW_SEC * _SR + (n_windows - 1) * _HOP_SEC * _SR
    t = np.linspace(0, total_samples / _SR, total_samples, dtype=np.float64)
    return (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float64)


def _patch_librosa(monkeypatch: pytest.MonkeyPatch, audio: np.ndarray) -> None:
    """Replace librosa with a minimal fake that avoids numba and real DSP."""
    n = len(audio)
    rms_frames = np.full(100, -20.0, dtype=np.float64)
    chroma = np.zeros((12, 50), dtype=np.float64)
    chroma[0, :] = 1.0  # C dominant

    fake = SimpleNamespace(
        load=lambda *a, **k: (audio, _SR),
        get_duration=lambda **k: n / _SR,
        effects=SimpleNamespace(hpss=lambda seg: (seg * 0.7, seg * 0.3)),
        feature=SimpleNamespace(
            rms=lambda **k: np.array([rms_frames]),
            spectral_centroid=lambda **k: np.array([[800.0] * 50]),
            chroma_cqt=lambda **k: chroma,
            spectral_flatness=lambda **k: np.array([[0.01] * 50]),
        ),
        beat=SimpleNamespace(beat_track=lambda **k: (np.array([120.0]), np.arange(10))),
        onset=SimpleNamespace(onset_detect=lambda **k: np.array([0, 5, 10])),
        stft=lambda seg, **k: np.ones((1025, 50), dtype=np.float64) * 0.1,
        fft_frequencies=lambda **k: np.linspace(0, _SR / 2, 1025),
        amplitude_to_db=lambda x, **k: np.full_like(x, -20.0),
    )
    monkeypatch.setattr(temporal_segmentation, "librosa", fake)


def test_analyze_emits_required_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    audio = _make_segment_audio(3)
    _patch_librosa(monkeypatch, audio)
    result = temporal_segmentation.analyze(Path("song.mp3"))
    assert set(result) >= _REQUIRED_KEYS


def test_snapshots_have_correct_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    audio = _make_segment_audio(3)
    _patch_librosa(monkeypatch, audio)
    result = temporal_segmentation.analyze(Path("song.mp3"))
    snaps = result["snapshots"]
    assert isinstance(snaps, list)
    assert len(snaps) >= 1
    assert isinstance(snaps[0], dict)
    assert set(snaps[0]) >= _SNAPSHOT_KEYS


def test_three_snapshots_produce_arc(monkeypatch: pytest.MonkeyPatch) -> None:
    audio = _make_segment_audio(3)
    _patch_librosa(monkeypatch, audio)
    result = temporal_segmentation.analyze(Path("song.mp3"))
    narr = result["narrative"]
    assert isinstance(narr, dict)
    # with ≥3 windows the arc key must be present
    assert "arc" in narr


def test_short_audio_no_windows_returns_empty_snapshots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Audio shorter than one window — no snapshots, narrative must be {}
    short = np.zeros(_SR * 5, dtype=np.float64)
    _patch_librosa(monkeypatch, short)
    result = temporal_segmentation.analyze(Path("short.wav"))
    assert result["snapshots"] == []
    assert result["narrative"] == {}


def test_two_snapshots_arc_absent_no_nan(monkeypatch: pytest.MonkeyPatch) -> None:
    # ISSUE-005: 2 windows -> len//3 == 0 -> arc must be absent, never NaN
    audio = _make_segment_audio(2)
    _patch_librosa(monkeypatch, audio)
    result = temporal_segmentation.analyze(Path("short.wav"))
    snaps = result["snapshots"]
    assert isinstance(snaps, list)
    narr = result["narrative"]
    assert isinstance(narr, dict)
    # arc absent or not present — must not contain NaN
    assert "arc" not in narr

    def _has_nan(obj: object) -> bool:
        if isinstance(obj, float):
            import math

            return not math.isfinite(obj)
        if isinstance(obj, dict):
            return any(_has_nan(v) for v in obj.values())
        if isinstance(obj, list):
            return any(_has_nan(v) for v in obj)
        return False

    assert not _has_nan(result)


def test_narrative_keys_present_with_three_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = _make_segment_audio(4)
    _patch_librosa(monkeypatch, audio)
    result = temporal_segmentation.analyze(Path("song.mp3"))
    narr = result["narrative"]
    assert isinstance(narr, dict)
    for key in ("climax", "quietest", "peak_tension", "transitions", "key_changes", "arc"):
        assert key in narr, f"Missing narrative key: {key}"
