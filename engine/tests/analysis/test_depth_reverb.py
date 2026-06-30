"""depth_reverb.analyze: output contract, rt60_std optional, defensive coercion."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import numpy as np

from claudes_ears.analysis import depth_reverb

if TYPE_CHECKING:
    import pytest

_SR = 22050

_REQUIRED_KEYS = {
    "duration",
    "rt60_estimate",
    "pre_delay_ms",
    "spectral_persistence",
    "spectral_flatness_mean",
    "spectral_flatness_std",
    "wetness_index",
    "room_size",
    "perceived_distance",
    "spatial_placement",
}


def _make_audio(n: int = _SR * 10) -> np.ndarray:
    t = np.linspace(0, n / _SR, n, dtype=np.float64)
    return (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float64)


def _patch_librosa(
    monkeypatch: pytest.MonkeyPatch,
    audio: np.ndarray,
    *,
    onset_frames: np.ndarray | None = None,
) -> None:
    if onset_frames is None:
        onset_frames = np.array([0, 20, 40], dtype=np.intp)

    stft_mat = np.ones((1025, 100), dtype=np.float64) * 0.1
    flat = np.full(100, 0.02, dtype=np.float64)

    fake = SimpleNamespace(
        load=lambda *a, **k: (audio, _SR),
        get_duration=lambda **k: len(audio) / _SR,
        onset=SimpleNamespace(onset_detect=lambda **k: onset_frames),
        frames_to_time=lambda frames, **k: np.asarray(frames, dtype=np.float64) * 0.5,
        stft=lambda y, **k: stft_mat,
        feature=SimpleNamespace(spectral_flatness=lambda **k: np.array([flat])),
    )
    monkeypatch.setattr(depth_reverb, "librosa", fake)


def test_analyze_emits_required_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    audio = _make_audio()
    _patch_librosa(monkeypatch, audio)
    result = depth_reverb.analyze(Path("song.mp3"))
    assert set(result) >= _REQUIRED_KEYS


def test_no_onsets_omits_rt60_std(monkeypatch: pytest.MonkeyPatch) -> None:
    # No decay_times collected -> rt60_std must be absent (optional)
    audio = _make_audio(_SR * 1)  # short; onset windows won't produce valid decays
    _patch_librosa(monkeypatch, audio, onset_frames=np.array([], dtype=np.intp))
    result = depth_reverb.analyze(Path("short.wav"))
    assert result["rt60_estimate"] == 0.0
    assert "rt60_std" not in result


def test_wetness_index_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    audio = _make_audio()
    _patch_librosa(monkeypatch, audio)
    result = depth_reverb.analyze(Path("song.mp3"))
    wi = result["wetness_index"]
    assert wi is None or (isinstance(wi, float) and 0.0 <= wi <= 1.0)


def test_room_labels_present(monkeypatch: pytest.MonkeyPatch) -> None:
    audio = _make_audio()
    _patch_librosa(monkeypatch, audio)
    result = depth_reverb.analyze(Path("song.mp3"))
    assert isinstance(result["room_size"], str)
    assert isinstance(result["perceived_distance"], str)
    assert isinstance(result["spatial_placement"], str)


def test_no_nan_in_result(monkeypatch: pytest.MonkeyPatch) -> None:
    audio = _make_audio()
    _patch_librosa(monkeypatch, audio)
    result = depth_reverb.analyze(Path("song.mp3"))

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


def test_room_label_mapping() -> None:
    assert depth_reverb._room_label(2.0)[0] == "cathedral / large hall"
    assert depth_reverb._room_label(1.0)[0] == "concert hall / large studio"
    assert depth_reverb._room_label(0.5)[0] == "medium room / studio"
    assert depth_reverb._room_label(0.2)[0] == "small room / vocal booth"
    assert depth_reverb._room_label(0.1)[0] == "dry / close-mic / no room"


def test_spatial_placement_mapping() -> None:
    assert "far" in depth_reverb._spatial_placement(50.0)
    assert "moderately" in depth_reverb._spatial_placement(25.0)
    assert "close to reflective" in depth_reverb._spatial_placement(10.0)
    assert "direct" in depth_reverb._spatial_placement(2.0)
