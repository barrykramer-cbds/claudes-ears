"""harmonic_rhythm.analyze: output contract, degraded inputs, issue fixes."""

from __future__ import annotations

from typing import cast

from claudes_ears.analysis import harmonic_rhythm

_REQUIRED_KEYS = {
    "total_chord_events",
    "total_changes",
    "tempo_bpm",
    "duration",
    "avg_changes_per_bar",
    "max_changes_per_bar",
    "min_changes_per_bar",
    "harmonic_arc",
    "total_phases",
    "total_accel_events",
    "phases",
    "acceleration_events",
    "windows",
}


def _make_chords(
    chord_sequence: list[tuple[str, float, float]],
    tempo: float = 120.0,
) -> dict[str, object]:
    """Build a minimal chord_progression-shaped dict from (chord, start, end) triples."""
    segments: list[dict[str, object]] = [
        {"chord": chord, "start": start, "end": end, "avg_confidence": 0.9}
        for chord, start, end in chord_sequence
    ]
    return {"tempo": tempo, "segments": segments}


def _alternating(n_bars: int = 16, tempo: float = 120.0) -> dict[str, object]:
    """C and G alternating every 2 s, producing many chord changes."""
    beat = 60.0 / tempo
    bar = 4 * beat
    pairs = [("C", i * bar, i * bar + bar / 2) for i in range(n_bars)] + [
        ("G", i * bar + bar / 2, (i + 1) * bar) for i in range(n_bars)
    ]
    pairs.sort(key=lambda x: x[1])
    return _make_chords(pairs, tempo)


def test_empty_segments_returns_degraded_contract() -> None:
    result = harmonic_rhythm.analyze({"tempo": 120.0, "segments": []})
    assert set(result) >= _REQUIRED_KEYS
    assert result["windows"] == []
    assert result["phases"] == []
    assert result["total_chord_events"] == 0


def test_missing_segments_key_returns_degraded_contract() -> None:
    result = harmonic_rhythm.analyze({"tempo": 120.0})
    assert set(result) >= _REQUIRED_KEYS
    assert result["windows"] == []


def test_zero_tempo_does_not_raise() -> None:
    # ISSUE-011: zero tempo caused ZeroDivisionError; should fall back to 120 BPM.
    chords = _alternating(tempo=120.0)
    chords["tempo"] = 0.0
    result = harmonic_rhythm.analyze(chords)
    assert set(result) >= _REQUIRED_KEYS
    assert result["tempo_bpm"] == 120.0


def test_absent_tempo_does_not_raise() -> None:
    chords = _alternating()
    del chords["tempo"]
    result = harmonic_rhythm.analyze(chords)
    assert set(result) >= _REQUIRED_KEYS
    assert result["tempo_bpm"] == 120.0


def test_canonical_field_name_is_windows_not_harmonic_rhythm_windows() -> None:
    # Schema §5 canonical key is "windows"; "harmonic_rhythm_windows" must never appear.
    result = harmonic_rhythm.analyze(_alternating())
    assert "windows" in result
    assert "harmonic_rhythm_windows" not in result


def test_full_result_emits_required_keys() -> None:
    result = harmonic_rhythm.analyze(_alternating())
    assert set(result) >= _REQUIRED_KEYS


def test_windows_populated_for_active_progression() -> None:
    result = harmonic_rhythm.analyze(_alternating(n_bars=32))
    assert isinstance(result["windows"], list)
    assert len(result["windows"]) > 0


def test_single_chord_produces_no_changes_degraded() -> None:
    chords = _make_chords([("C", 0.0, 120.0)])
    result = harmonic_rhythm.analyze(chords)
    assert set(result) >= _REQUIRED_KEYS
    assert result["total_changes"] == 0
    assert result["windows"] == []


def test_fewer_than_two_changes_returns_degraded() -> None:
    # Only one change: C -> G, no second change for interval calculation.
    chords = _make_chords([("C", 0.0, 60.0), ("G", 60.0, 120.0)])
    result = harmonic_rhythm.analyze(chords)
    assert set(result) >= _REQUIRED_KEYS
    assert cast("int", result["total_changes"]) == 1
    assert result["windows"] == []


def test_phases_non_empty_for_multi_section_progression() -> None:
    result = harmonic_rhythm.analyze(_alternating(n_bars=32))
    assert isinstance(result["phases"], list)
    assert len(result["phases"]) >= 1
    for phase in result["phases"]:
        assert "class" in phase
        assert "avg_changes_per_bar" in phase
        assert "narrative" in phase


def test_output_is_json_serialisable() -> None:
    import json

    result = harmonic_rhythm.analyze(_alternating())
    json.dumps(result)  # must not raise
