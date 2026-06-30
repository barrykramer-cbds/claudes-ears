"""emotional_trajectory.analyze: output contract, degraded inputs, ISSUE-005 guard."""

from __future__ import annotations

from typing import cast

from claudes_ears.analysis import emotional_trajectory

_REQUIRED_KEYS = {
    "total_windows",
    "total_transitions",
    "total_phases",
    "unique_states",
    "phases",
    "transitions",
    "trajectory_summary",
    "narrative",
}

_PHASE_KEYS = {
    "state",
    "energy",
    "start",
    "end",
    "duration_s",
    "tension_trend",
    "avg_tension",
    "avg_warmth",
}


def _make_snap(
    time: str = "0:00",
    t_center: float = 0.0,
    tension: float = 0.002,
    warmth: float = 1.5,
    consonance: float = 0.55,
    rms_p90: float = -8.0,
    harm_pct: float = 80.0,
    onset_density: float = 3.0,
) -> dict[str, object]:
    return {
        "time": time,
        "t_center": t_center,
        "tension": tension,
        "warmth": warmth,
        "consonance": consonance,
        "rms_p90": rms_p90,
        "harm_pct": harm_pct,
        "onset_density": onset_density,
    }


def test_empty_temporal_returns_full_contract() -> None:
    """ISSUE-005: empty snapshots must return full shape, not raise or return error dict."""
    result = emotional_trajectory.analyze({})
    assert set(result) >= _REQUIRED_KEYS
    assert result["total_windows"] == 0
    assert result["phases"] == []
    assert result["transitions"] == []
    assert result["trajectory_summary"] == []
    assert "error" not in result


def test_empty_snapshots_list_returns_full_contract() -> None:
    result = emotional_trajectory.analyze({"snapshots": []})
    assert set(result) >= _REQUIRED_KEYS
    assert result["total_windows"] == 0
    assert result["total_phases"] == 0
    assert "error" not in result


def test_single_snapshot_no_nan() -> None:
    """ISSUE-005: single snapshot must not produce NaN in avg_tension/avg_warmth."""
    result = emotional_trajectory.analyze({"snapshots": [_make_snap()]})
    assert set(result) >= _REQUIRED_KEYS
    phases = result["phases"]
    assert isinstance(phases, list)
    assert len(phases) == 1
    phase = phases[0]
    assert isinstance(phase, dict)
    assert set(phase) >= _PHASE_KEYS
    # avg_tension and avg_warmth must be finite floats (not NaN)
    avg_t = phase["avg_tension"]
    avg_w = phase["avg_warmth"]
    assert avg_t is not None
    assert avg_w is not None
    import math

    assert math.isfinite(float(avg_t))
    assert math.isfinite(float(avg_w))


def test_two_snapshots_no_nan() -> None:
    """ISSUE-005: fewer than 3 snapshots must not produce NaN anywhere."""
    snaps = [_make_snap("0:00", 0.0), _make_snap("0:15", 15.0)]
    result = emotional_trajectory.analyze({"snapshots": snaps})
    assert result["total_windows"] == 2
    for phase in cast("list[dict[str, object]]", result["phases"]):
        assert isinstance(phase, dict)
        assert phase.get("avg_tension") is not None
        assert phase.get("avg_warmth") is not None


def test_multiple_snapshots_same_state_single_phase() -> None:
    snaps = [
        _make_snap("0:00", 0.0),
        _make_snap("0:15", 15.0),
        _make_snap("0:30", 30.0),
    ]
    result = emotional_trajectory.analyze({"snapshots": snaps})
    assert result["total_phases"] == 1
    assert result["total_transitions"] == 0
    phases = result["phases"]
    assert isinstance(phases, list)
    assert len(phases) == 1


def test_state_transition_detected() -> None:
    snaps = [
        _make_snap("0:00", 0.0, tension=0.0, warmth=3.0, consonance=0.7),  # deep peace
        _make_snap("0:15", 15.0, tension=0.005, warmth=1.0),  # cold tension
    ]
    result = emotional_trajectory.analyze({"snapshots": snaps})
    assert result["total_transitions"] == 1
    assert result["total_phases"] == 2
    transitions = result["transitions"]
    assert isinstance(transitions, list)
    first = transitions[0]
    assert isinstance(first, dict)
    assert "from_state" in first
    assert "to_state" in first
    assert first["from_state"] != first["to_state"]


def test_trajectory_summary_length_matches_windows() -> None:
    snaps = [_make_snap(f"0:{i * 15:02d}", float(i * 15)) for i in range(5)]
    result = emotional_trajectory.analyze({"snapshots": snaps})
    summary = result["trajectory_summary"]
    assert isinstance(summary, list)
    assert len(summary) == 5
    for entry in summary:
        assert isinstance(entry, dict)
        assert "time" in entry
        assert "state" in entry
        assert "energy" in entry


def test_narrative_is_non_empty_with_valid_snaps() -> None:
    snaps = [_make_snap("0:00", 0.0), _make_snap("0:15", 15.0)]
    result = emotional_trajectory.analyze({"snapshots": snaps})
    assert isinstance(result["narrative"], str)
    assert len(str(result["narrative"])) > 0


def test_none_snapshot_values_handled_safely() -> None:
    """Snapshot with all-None values must not crash or produce NaN."""
    snap: dict[str, object] = {
        "time": None,
        "t_center": None,
        "tension": None,
        "warmth": None,
        "consonance": None,
        "rms_p90": None,
        "harm_pct": None,
        "onset_density": None,
    }
    result = emotional_trajectory.analyze({"snapshots": [snap]})
    assert set(result) >= _REQUIRED_KEYS
    assert result["total_windows"] == 1
