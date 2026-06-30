"""Groove timing: the three root shapes (two errors + full) and the timing math."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from claudes_ears.analysis import groove_timing
from claudes_ears.analysis.groove_timing import (
    _beat_deviations,
    _distribution,
    _drift,
    _feel,
    _swing,
    _tightness,
)


def _patch_librosa(
    monkeypatch: pytest.MonkeyPatch,
    *,
    beats: object,
    onsets: object,
    tempo: float = 120.0,
    duration: float = 16.0,
) -> MagicMock:
    """Stub librosa at the boundary; frames_to_time is identity so we pass seconds in."""
    m = MagicMock()
    m.load.return_value = (np.zeros(8, dtype=np.float64), 22050)
    m.get_duration.return_value = duration
    m.beat.beat_track.return_value = (
        np.array([tempo]),
        np.asarray(beats, dtype=np.float64),
    )
    m.onset.onset_detect.return_value = np.asarray(onsets, dtype=np.float64)
    m.frames_to_time.side_effect = lambda frames, sr=None: np.asarray(frames, dtype=np.float64)
    monkeypatch.setattr(groove_timing, "librosa", m)
    return m


def test_full_shape_reports_feel_swing_drift_and_distribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    beats = np.arange(0.0, 16.0, 0.5)
    onsets = beats + 0.003  # uniformly 3ms behind the grid
    _patch_librosa(monkeypatch, beats=beats, onsets=onsets)

    result = groove_timing.analyze(object())  # type: ignore[arg-type]

    assert result["beat_count"] == len(beats)
    assert result["mean_deviation_ms"] == pytest.approx(3.0)
    assert result["feel"] == "slightly behind (relaxed feel)"
    assert result["tightness"] == "machine-tight (quantized or extremely precise)"
    assert result["swing_character"] == "straight (no swing)"
    assert result["drift"] == "stable timing (no drift)"
    assert result["timing_distribution"] == {
        "behind_pct": 100.0,
        "on_grid_pct": 0.0,
        "ahead_pct": 0.0,
    }


def test_insufficient_beats_returns_error_shape_without_onset_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    m = _patch_librosa(monkeypatch, beats=[0.0, 0.5, 1.0], onsets=[])

    result = groove_timing.analyze(object())  # type: ignore[arg-type]

    assert result["error"] == "insufficient beats detected"
    assert result["beat_count"] == 3
    assert "mean_deviation_ms" not in result
    assert "feel" not in result
    m.onset.onset_detect.assert_not_called()


def test_too_few_onset_pairs_returns_error_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    beats = np.arange(0.0, 8.0, 0.5)
    _patch_librosa(monkeypatch, beats=beats, onsets=[0.0, 0.5, 1.0, 1.5, 2.0])

    result = groove_timing.analyze(object())  # type: ignore[arg-type]

    assert result["error"] == "insufficient onset-beat pairs"
    assert "feel" not in result
    assert "timing_distribution" not in result


def test_empty_onsets_falls_into_onset_pair_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_librosa(monkeypatch, beats=np.arange(0.0, 8.0, 0.5), onsets=[])

    result = groove_timing.analyze(object())  # type: ignore[arg-type]

    assert result["error"] == "insufficient onset-beat pairs"


def test_beat_deviations_drops_onsets_past_half_beat() -> None:
    beats = np.array([0.0, 0.5], dtype=np.float64)
    onsets = np.array([0.003, 5.0], dtype=np.float64)  # second is > half a beat away

    devs = _beat_deviations(onsets, beats, tempo=120.0)

    assert devs.tolist() == pytest.approx([3.0])


@pytest.mark.parametrize(
    ("mean_dev", "expected"),
    [
        (6.0, "behind the beat (lazy / heavy / groove)"),
        (3.0, "slightly behind (relaxed feel)"),
        (0.0, "on the grid (mechanical / precise)"),
        (-3.0, "slightly ahead (driving feel)"),
        (-6.0, "ahead of the beat (pushing / anxious / urgent)"),
    ],
)
def test_feel_thresholds(mean_dev: float, expected: str) -> None:
    assert _feel(mean_dev) == expected


@pytest.mark.parametrize(
    ("std_dev", "expected"),
    [
        (1.0, "machine-tight (quantized or extremely precise)"),
        (7.0, "tight (skilled performer)"),
        (15.0, "human (natural variation)"),
        (25.0, "loose (deliberate or amateur)"),
        (50.0, "very loose (freeform or intentionally sloppy)"),
    ],
)
def test_tightness_thresholds(std_dev: float, expected: str) -> None:
    assert _tightness(std_dev) == expected


def test_swing_returns_empty_when_too_few_onsets() -> None:
    assert _swing(np.arange(0.0, 5.0, 0.5)) == {}


def test_drift_returns_empty_when_too_few_deviations() -> None:
    assert _drift(np.zeros(10, dtype=np.float64)) == {}


def test_distribution_percentages_sum_to_one_hundred() -> None:
    deviations = np.array([5.0, -5.0, 0.0, 0.0], dtype=np.float64)

    dist = _distribution(deviations)

    assert dist["behind_pct"] == pytest.approx(25.0)
    assert dist["ahead_pct"] == pytest.approx(25.0)
    assert dist["on_grid_pct"] == pytest.approx(50.0)
