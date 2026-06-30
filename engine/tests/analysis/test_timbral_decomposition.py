"""Tests for NMF timbral decomposition — happy path, ISSUE-006 bound, degraded input."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from claudes_ears.analysis import timbral_decomposition as td

_LoadPatcher = Callable[..., AbstractContextManager[object]]


def _tone(n_samples: int, sr: int = 22050, freq: float = 440.0) -> np.ndarray:
    t = np.arange(n_samples) / sr
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


@pytest.fixture
def patched_load() -> _LoadPatcher:
    def _apply(signal: np.ndarray, sr: int = 22050) -> AbstractContextManager[object]:
        target = "claudes_ears.analysis.timbral_decomposition.librosa.load"
        return patch(target, return_value=(signal, sr))

    return _apply


def test_happy_path_returns_ranked_components(patched_load: _LoadPatcher) -> None:
    with patched_load(_tone(22050)):
        result = td.analyze(Path("other.wav"), n_components=3)

    assert result["n_components"] == 3
    components = result["components"]
    assert isinstance(components, list)
    assert len(components) == 3
    ranks = [c["rank"] for c in components]
    assert ranks == [1, 2, 3]
    energies = [c["energy_contribution"] for c in components]
    assert energies == sorted(energies, reverse=True)
    assert all(isinstance(c["instrument_guess"], str) for c in components)


def test_short_audio_bounds_n_components(patched_load: _LoadPatcher) -> None:
    """ISSUE-006: a tiny spectrogram must not crash NMF; rank clamps below the request."""
    with patched_load(_tone(1024)):
        result = td.analyze(Path("tiny.wav"), n_components=8)

    n = result["n_components"]
    components = result["components"]
    assert isinstance(n, int)
    assert isinstance(components, list)
    assert 1 <= n < 8
    assert len(components) == n


def test_bound_clamps_to_frame_count() -> None:
    spectrogram = np.ones((1025, 2), dtype=np.float64)
    assert td._bound_components(8, spectrogram) == 2


def test_bound_floors_at_one() -> None:
    spectrogram = np.ones((1025, 0), dtype=np.float64)
    assert td._bound_components(4, spectrogram) == 1


def test_empty_audio_returns_degraded(patched_load: _LoadPatcher) -> None:
    with patched_load(np.array([], dtype=np.float32)):
        result = td.analyze(Path("empty.wav"))

    assert result["n_components"] == 0
    assert result["components"] == []
    assert result["reconstruction_error"] is None


def test_output_is_json_safe(patched_load: _LoadPatcher) -> None:
    import json

    with patched_load(_tone(22050)):
        result = td.analyze(Path("other.wav"), n_components=2)

    json.dumps(result)  # sanitized output must serialize without a custom encoder


def test_classify_returns_name_and_score() -> None:
    name, score = td.classify_component(centroid=120.0, harmonic_pct=80.0, attack_sharpness=0.1)
    assert isinstance(name, str)
    assert isinstance(score, float)
