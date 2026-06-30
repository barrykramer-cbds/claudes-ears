"""Breath detection: full vs empty root shape, and degraded inputs (schema §5)."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from claudes_ears.analysis import breath_detection as bd
from claudes_ears.models.perception import BreathDetection

_DURATION = 2.322


def _fake_librosa(
    rms: np.ndarray,
    flatness: np.ndarray,
    centroid: np.ndarray,
    harm_rms: np.ndarray,
    duration: float = _DURATION,
) -> SimpleNamespace:
    """librosa stand-in: feature.rms yields the stem rms then the harmonic rms."""
    calls = {"rms": 0}

    def _rms(**_: object) -> np.ndarray:
        out = rms if calls["rms"] == 0 else harm_rms
        calls["rms"] += 1
        return out[np.newaxis, :]

    return SimpleNamespace(
        load=lambda *_, **__: (np.zeros(10), bd._SR),
        get_duration=lambda **_: duration,
        feature=SimpleNamespace(
            rms=_rms,
            spectral_flatness=lambda **_: flatness[np.newaxis, :],
            spectral_centroid=lambda **_: centroid[np.newaxis, :],
        ),
        effects=SimpleNamespace(harmonic=lambda y: y),
    )


def _two_breath_arrays() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """100 frames: singing | breath(13) | mid | breath(7) | silence — yields 2 events."""
    rms = np.empty(100)
    rms[0:25] = 1.0
    rms[25:38] = 0.10
    rms[38:63] = 0.9
    rms[63:70] = 0.10
    rms[70:100] = 0.01

    flatness = np.full(100, 0.01)
    flatness[0:25] = 0.1
    flatness[25:38] = 0.5
    flatness[63:70] = 0.5

    centroid = np.full(100, 2000.0)

    harm_rms = rms.copy()
    harm_rms[25:38] = 0.05
    harm_rms[63:70] = 0.05
    return rms, flatness, centroid, harm_rms


def test_full_shape_detects_breaths_and_parses_into_model(monkeypatch: pytest.MonkeyPatch) -> None:
    rms, flatness, centroid, harm_rms = _two_breath_arrays()
    monkeypatch.setattr(bd, "librosa", _fake_librosa(rms, flatness, centroid, harm_rms))

    result = bd.analyze(Path("vocals.wav"))

    assert result["total_breaths"] == 2
    events = result["breath_events"]
    assert isinstance(events, list)
    assert len(events) == 2
    assert result["depth_distribution"] == {"deep": 0, "normal": 1, "catch": 1}
    assert result["context_distribution"] == {"phrase end": 2}
    assert isinstance(result["breaths_per_minute"], float)
    assert result["min_inter_breath_interval_s"] == result["max_inter_breath_interval_s"]
    BreathDetection.model_validate(result)


def test_empty_shape_when_no_breaths_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    rms, _, centroid, harm_rms = _two_breath_arrays()
    flat = np.zeros(100)  # nothing clears the flatness gate -> no breath frames
    monkeypatch.setattr(bd, "librosa", _fake_librosa(rms, flat, centroid, harm_rms))

    result = bd.analyze(Path("vocals.wav"))

    assert result["total_breaths"] == 0
    assert result["breath_events"] == []
    assert "min_inter_breath_interval_s" not in result
    assert "max_inter_breath_interval_s" not in result
    assert isinstance(result["breaths_per_minute"], float)
    BreathDetection.model_validate(result)


def test_no_singing_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    flat = np.full(50, 0.5)
    uniform = np.full(50, 0.5)  # rms > median is empty -> no singing anchor
    monkeypatch.setattr(bd, "librosa", _fake_librosa(uniform, flat, flat, uniform))

    result = bd.analyze(Path("vocals.wav"))

    assert result["total_breaths"] == 0
    assert result["duration"] == round(_DURATION, 2)


def test_empty_audio_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    empty = np.array([])
    monkeypatch.setattr(bd, "librosa", _fake_librosa(empty, empty, empty, empty, duration=0.0))

    result = bd.analyze(Path("vocals.wav"))

    assert result["total_breaths"] == 0
    assert result["duration"] == 0.0
    BreathDetection.model_validate(result)
