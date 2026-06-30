"""Vocal narrative: phase segmentation, call-response, and the ISSUE-002 all-zero frame."""

from __future__ import annotations

from pathlib import Path
import sys
import types
from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

_SR = 22050
_WINDOW = 3.0
_WINDOW_SAMPLES = int(_WINDOW * _SR)


class _FakeLibrosa:
    """Minimal librosa stand-in; per-test attributes shape the analysis inputs."""

    def __init__(self) -> None:
        self.signal = np.zeros(_WINDOW_SAMPLES, dtype=np.float64)
        self.cqt_frame = np.zeros(60, dtype=np.float64)
        self.pitches = np.zeros((10, 4), dtype=np.float64)
        self.magnitudes = np.zeros((10, 4), dtype=np.float64)
        self.flatness = 0.01
        self.harmonic_scale = 0.9
        self.feature = types.SimpleNamespace(spectral_flatness=self._spectral_flatness)
        self.effects = types.SimpleNamespace(harmonic=self._harmonic)

    def load(self, _path: str, sr: int = _SR, mono: bool = True) -> tuple[np.ndarray, int]:
        return self.signal, sr

    def get_duration(self, y: np.ndarray, sr: int) -> float:
        return len(y) / sr

    def note_to_hz(self, _note: str) -> float:
        return 65.41

    def cqt(self, seg: np.ndarray, **_kwargs: object) -> np.ndarray:
        return np.tile(self.cqt_frame[:, None], (1, 3))

    def piptrack(self, y: np.ndarray, **_kwargs: object) -> tuple[np.ndarray, np.ndarray]:
        return self.pitches, self.magnitudes

    def _spectral_flatness(self, y: np.ndarray) -> np.ndarray:
        return np.full((1, 4), self.flatness, dtype=np.float64)

    def _harmonic(self, seg: np.ndarray) -> np.ndarray:
        return seg * self.harmonic_scale


@pytest.fixture
def fake_librosa() -> Iterator[_FakeLibrosa]:
    fake = _FakeLibrosa()
    sys.modules["librosa"] = fake  # type: ignore[assignment]  # module stand-in for import
    yield fake
    sys.modules.pop("librosa", None)


def _analyze(_fake: _FakeLibrosa) -> dict[str, object]:
    import importlib

    from claudes_ears.analysis import vocal_narrative

    # reload re-runs `import librosa`, rebinding to the fixture's fake each call.
    importlib.reload(vocal_narrative)
    return vocal_narrative.analyze(Path("vocals.wav"), sr=_SR, window_sec=_WINDOW)


def _loud_signal(n_windows: int) -> np.ndarray:
    return np.full(_WINDOW_SAMPLES * n_windows, 0.3, dtype=np.float64)


def test_silence_signal_yields_silence_phase(fake_librosa: _FakeLibrosa) -> None:
    fake_librosa.signal = np.zeros(_WINDOW_SAMPLES * 2, dtype=np.float64)
    result = _analyze(fake_librosa)
    assert result["total_phases"] == 1
    phases = result["phases"]
    assert isinstance(phases, list)
    assert phases[0]["type"] == "silence"


def test_sparse_peaks_classified_as_solo(fake_librosa: _FakeLibrosa) -> None:
    fake_librosa.signal = _loud_signal(2)
    fake_librosa.cqt_frame[20] = 1.0  # single dominant partial -> few peaks
    fake_librosa.harmonic_scale = 0.97
    result = _analyze(fake_librosa)
    segments = result["segments"]
    assert isinstance(segments, list)
    assert all(s["type"] == "solo" for s in segments)


def test_dense_peaks_classified_as_chorus(fake_librosa: _FakeLibrosa) -> None:
    fake_librosa.signal = _loud_signal(2)
    fake_librosa.cqt_frame[1:-1:2] = 1.0  # many alternating partials -> dense peaks
    fake_librosa.flatness = 0.08
    fake_librosa.harmonic_scale = 0.5
    result = _analyze(fake_librosa)
    segments = result["segments"]
    assert isinstance(segments, list)
    assert all(s["type"] in {"chorus", "lead_with_backing"} for s in segments)


def test_all_zero_piptrack_frame_does_not_crash(fake_librosa: _FakeLibrosa) -> None:
    """ISSUE-002: a frame with no pitch energy must not raise on indexing."""
    fake_librosa.signal = _loud_signal(1)
    fake_librosa.cqt_frame[20] = 1.0
    fake_librosa.pitches = np.zeros((10, 3), dtype=np.float64)
    fake_librosa.magnitudes = np.zeros((10, 3), dtype=np.float64)  # all-zero -> guarded path
    result = _analyze(fake_librosa)
    segments = result["segments"]
    assert isinstance(segments, list)
    assert segments[0]["pitch_spread"] == 0
    assert segments[0]["pitch_mean"] == 0


def test_empty_signal_yields_no_phases(fake_librosa: _FakeLibrosa) -> None:
    fake_librosa.signal = np.zeros(0, dtype=np.float64)
    result = _analyze(fake_librosa)
    assert result["total_phases"] == 0
    assert result["segments"] == []
    assert result["type_distribution"] == {}


def test_pitch_spread_uses_strong_frames(fake_librosa: _FakeLibrosa) -> None:
    fake_librosa.signal = _loud_signal(1)
    fake_librosa.cqt_frame[20] = 1.0
    pitches = np.zeros((10, 2), dtype=np.float64)
    mags = np.zeros((10, 2), dtype=np.float64)
    # Magnitudes spread so the median threshold keeps the loudest two pitches.
    pitches[:4, 0] = np.array([100, 200, 300, 400], dtype=np.float64)
    mags[:4, 0] = np.array([1, 2, 3, 4], dtype=np.float64)
    fake_librosa.pitches = pitches
    fake_librosa.magnitudes = mags
    result = _analyze(fake_librosa)
    segments = result["segments"]
    assert isinstance(segments, list)
    assert segments[0]["pitch_spread"] > 0
    assert segments[0]["pitch_mean"] > 0
