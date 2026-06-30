"""Behavior tests for the vocal_relationships analysis step."""

from __future__ import annotations

import librosa
import numpy as np
import pytest

from claudes_ears.analysis import vocal_relationships as vr

_UNION = {"solo", "support", "dialogue", "opposition", "merge", "withdraw", "silence"}


@pytest.mark.parametrize(
    ("density", "density_change", "lead_present", "register", "prev", "expected"),
    [
        (1, 0, True, "none", "silence", "solo"),
        (1, -1, True, "none", "support", "withdraw"),
        (3, 1, True, "below", "solo", "support"),
        (3, 1, True, "both", "solo", "merge"),
        (2, 1, True, "above", "solo", "dialogue"),
        (2, 0, False, "none", "solo", "opposition"),
    ],
)
def test_classify_covers_label_union(
    density: int,
    density_change: int,
    lead_present: bool,
    register: str,
    prev: str,
    expected: str,
) -> None:
    label, narrative = vr._classify(density, density_change, lead_present, register, prev)
    assert label == expected
    assert label in _UNION
    assert narrative


def test_silence_moment_drops_register_keys() -> None:
    moment = vr._silence_moment(61.5, -60.0, "silence")
    assert moment["relationship"] == "silence"
    assert moment["label"] == "1:01"
    assert moment["lead_present"] is False
    for dropped in ("lead_pct", "below_pct", "above_pct"):
        assert dropped not in moment


def test_build_story_merges_consecutive_relationships() -> None:
    moments = [
        vr._silence_moment(0.0, -60.0, "silence"),
        {"relationship": "solo", "narrative": "n", "label": "0:01", "time": 1.0, "density": 1},
        {"relationship": "solo", "narrative": "n", "label": "0:02", "time": 2.0, "density": 1},
        {"relationship": "support", "narrative": "m", "label": "0:03", "time": 3.0, "density": 3},
    ]
    story = vr._build_story(moments)
    assert [phase["relationship"] for phase in story] == ["silence", "solo", "support"]
    assert story[1]["avg_density"] == 1.0
    assert story[1]["duration_s"] == 2.0


def _patch_librosa(
    monkeypatch: pytest.MonkeyPatch,
    samples: np.ndarray,
    *,
    piptrack: tuple[np.ndarray, np.ndarray] | None = None,
    sr: int = vr._SR,
) -> None:
    monkeypatch.setattr(librosa, "load", lambda *a, **k: (samples, float(sr)))
    monkeypatch.setattr(librosa, "get_duration", lambda *a, **k: len(samples) / sr)
    fallback = (np.zeros((4, 3)), np.zeros((4, 3)))
    monkeypatch.setattr(librosa, "piptrack", lambda *a, **k: piptrack or fallback)


def test_analyze_all_silence_drops_register_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_librosa(monkeypatch, np.zeros(5 * vr._SR, dtype=np.float64))
    result = vr.analyze(object())  # type: ignore[arg-type]

    assert result["moments"]
    for moment in result["moments"]:  # type: ignore[attr-defined]
        assert moment["relationship"] == "silence"
        assert "lead_pct" not in moment
    assert result["relationship_distribution"] == {"silence": 100.0}


def test_analyze_empty_input_is_degraded_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_librosa(monkeypatch, np.zeros(vr._SR // 10, dtype=np.float64))
    result = vr.analyze(object())  # type: ignore[arg-type]

    assert result["moments"] == []
    assert result["story"] == []
    assert result["transitions"] == []
    assert result["total_story_phases"] == 0
    assert result["relationship_distribution"] == {}


def test_analyze_active_frame_keeps_register_pcts(monkeypatch: pytest.MonkeyPatch) -> None:
    # Two strong pitches at 300 Hz so the percentile gate admits one as active,
    # forcing a single-cluster lead-present "solo" with concrete percentages.
    bins, frames = 4, 3
    pitches = np.zeros((bins, frames))
    mags = np.zeros((bins, frames))
    pitches[1, :] = 300.0
    pitches[2, :] = 300.0
    mags[1, :] = 0.5
    mags[2, :] = 1.0

    _patch_librosa(
        monkeypatch, np.full(3 * vr._SR, 0.5, dtype=np.float64), piptrack=(pitches, mags)
    )

    result = vr.analyze(object())  # type: ignore[arg-type]
    moments = result["moments"]
    assert moments
    moment = moments[0]  # type: ignore[index]
    assert moment["relationship"] in _UNION
    assert moment["lead_present"] is True
    assert isinstance(moment["lead_pct"], float)
    assert moment["lead_pct"] == 100.0
    assert "solo" in result["relationship_distribution"]  # type: ignore[operator]
