"""Tests for the vocal_intervals interval-profiling step."""

from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from claudes_ears.analysis import vocal_intervals

if TYPE_CHECKING:
    from pathlib import Path


def _two_peak_cqt(low_bin: int, high_bin: int, frames: int = 10) -> np.ndarray:
    """A CQT magnitude matrix with two sharp peaks per frame at the given bins."""
    cqt = np.zeros((vocal_intervals._N_BINS, frames), dtype=np.float64)
    cqt[low_bin, :] = 1.0
    cqt[high_bin, :] = 1.0
    return cqt


@pytest.mark.parametrize(
    ("semitones", "expected"),
    [(0, 0), (7, 7), (11, 11), (12, 12), (13, 1), (24, 12), (36, 12)],
)
def test_interval_class_preserves_octave(semitones: int, expected: int) -> None:
    assert vocal_intervals._interval_class(semitones) == expected


def test_octave_peaks_count_as_octave_not_unison() -> None:
    """ISSUE-010: a 12-semitone gap must land in the octave bucket, not unison.

    The pre-fix ``% 12`` collapsed 12 to 0, so the always-true guard left the
    octave bucket empty and miscounted octaves as unisons.
    """
    result = vocal_intervals._profile(_two_peak_cqt(10, 22), sr=vocal_intervals._SR, duration=5.0)
    entries = cast("list[dict[str, object]]", result["interval_profile"])
    profile = {entry["semitones"]: cast("int", entry["count"]) for entry in entries}

    assert profile[12] > 0
    assert profile[0] == 0
    assert cast("dict[str, object]", result["dominant_interval"])["name"] == "octave"


def test_perfect_fifth_profile() -> None:
    result = vocal_intervals._profile(_two_peak_cqt(10, 17), sr=vocal_intervals._SR, duration=5.0)

    assert cast("int", result["total_interval_events"]) > 0
    assert cast("dict[str, object]", result["dominant_interval"])["name"] == "perfect 5th"
    assert 0.0 <= cast("float", result["consonance_ratio"]) <= 1.0


def test_silent_input_is_degraded_not_error() -> None:
    silent = np.zeros((vocal_intervals._N_BINS, 20), dtype=np.float64)

    result = vocal_intervals._profile(silent, sr=vocal_intervals._SR, duration=3.0)

    assert result["total_interval_events"] == 0
    assert result["consonance_ratio"] == 0.0
    assert result["harmonic_character"] == "insufficient harmonic data"
    assert "dominant_interval" not in result


def test_analyze_mocks_librosa_at_boundary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The ml extra (librosa) is absent in this env, so inject a fake at the import boundary."""
    cqt = _two_peak_cqt(10, 22)
    fake = types.ModuleType("librosa")
    fake.load = lambda *a, **k: (np.zeros(1000), vocal_intervals._SR)  # type: ignore[attr-defined]
    fake.get_duration = lambda **k: 5.0  # type: ignore[attr-defined]
    fake.note_to_hz = lambda note: 65.0  # type: ignore[attr-defined]
    fake.cqt = lambda *a, **k: cqt  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "librosa", fake)

    result = vocal_intervals.analyze(tmp_path / "vocals.wav")

    assert result["duration"] == 5.0
    assert cast("dict[str, object]", result["dominant_interval"])["name"] == "octave"
