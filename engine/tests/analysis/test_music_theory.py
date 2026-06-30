"""music_theory.analyze: output contract, degraded inputs, issue fixes."""

from __future__ import annotations

import math

import pytest

from claudes_ears.analysis import music_theory

_REQUIRED_KEYS = {
    "key",
    "mode",
    "key_confidence",
    "total_chords",
    "unique_numerals",
    "harmonic_vocabulary_size",
    "chromatic_chords_pct",
    "total_cadences",
    "cadence_distribution",
    "cadences",
    "analyzed_chords",
}


def _make_chords(
    chord_sequence: list[tuple[str, float, float]],
) -> dict[str, object]:
    segments: list[dict[str, object]] = [
        {"chord": chord, "start": start, "end": end, "avg_confidence": 0.9}
        for chord, start, end in chord_sequence
    ]
    return {"tempo": 120.0, "segments": segments}


def _c_major_progression() -> dict[str, object]:
    """I-IV-V-I in C major, long durations for strong key detection."""
    return _make_chords(
        [
            ("C", 0.0, 8.0),
            ("F", 8.0, 16.0),
            ("G", 16.0, 24.0),
            ("C", 24.0, 32.0),
        ]
    )


def test_empty_segments_returns_degraded_contract() -> None:
    result = music_theory.analyze({"tempo": 120.0, "segments": []})
    assert set(result) >= _REQUIRED_KEYS
    assert result["analyzed_chords"] == []
    assert result["cadences"] == []
    assert result["unique_numerals"] == []
    assert result["total_chords"] == 0


def test_missing_segments_key_returns_degraded_contract() -> None:
    result = music_theory.analyze({"tempo": 120.0})
    assert set(result) >= _REQUIRED_KEYS


def test_full_result_emits_required_keys() -> None:
    result = music_theory.analyze(_c_major_progression())
    assert set(result) >= _REQUIRED_KEYS


def test_maj7_classified_as_major_not_minor() -> None:
    # ISSUE-003: 'm' in 'maj7'[:2] == 'ma' caused minor classification.
    assert music_theory._parse_chord_quality("Gmaj7") == "major"
    assert music_theory._parse_chord_quality("Cmaj7") == "major"
    assert music_theory._parse_chord_quality("Amaj7") == "major"


def test_minor_chords_still_classified_correctly() -> None:
    assert music_theory._parse_chord_quality("Am") == "minor"
    assert music_theory._parse_chord_quality("Am7") == "minor"
    assert music_theory._parse_chord_quality("Bmin") == "minor"


def test_parse_chord_quality_coverage() -> None:
    assert music_theory._parse_chord_quality("Cdim") == "diminished"
    assert music_theory._parse_chord_quality("Caug") == "augmented"
    assert music_theory._parse_chord_quality("C") == "major"
    assert music_theory._parse_chord_quality("C7") == "major"
    assert music_theory._parse_chord_quality("Csus4") == "suspended"


def test_unique_numerals_are_sorted() -> None:
    # ISSUE-003 / schema §5: list(set(...)) is nondeterministic; must be sorted.
    result = music_theory.analyze(_c_major_progression())
    numerals = result["unique_numerals"]
    assert isinstance(numerals, list)
    assert numerals == sorted(numerals)


def test_key_confidence_nan_becomes_none() -> None:
    # sanitize() converts NaN -> None; the field must never be a bare NaN float.
    result = music_theory.analyze(_c_major_progression())
    kc = result["key_confidence"]
    assert kc is None or (isinstance(kc, float) and math.isfinite(kc))


def test_key_detected_for_c_major() -> None:
    result = music_theory.analyze(_c_major_progression())
    assert result["key"] == "C"
    assert result["mode"] == "major"


def test_analyzed_chords_analysis_nullable() -> None:
    # Schema: analyzed_chords[].analysis is nullable — N.C. chords have analysis=None.
    chords = _make_chords([("N.C.", 0.0, 4.0), ("C", 4.0, 8.0)])
    result = music_theory.analyze(chords)
    entries = result["analyzed_chords"]
    assert isinstance(entries, list)
    no_chord_entries = [e for e in entries if e["chord"] == "N.C."]
    assert all(e["analysis"] is None for e in no_chord_entries)


def test_authentic_cadence_detected() -> None:
    # V -> I is an authentic cadence.
    chords = _make_chords([("G", 0.0, 4.0), ("C", 4.0, 8.0)])
    result = music_theory.analyze(chords)
    cadences = result["cadences"]
    assert isinstance(cadences, list)
    types = [c["type"] for c in cadences]
    assert "authentic" in types


def test_output_is_json_serialisable() -> None:
    import json

    result = music_theory.analyze(_c_major_progression())
    json.dumps(result)  # must not raise


@pytest.mark.parametrize(
    ("chord", "expected_quality"),
    [
        ("Gmaj7", "major"),
        ("Am7", "minor"),
        ("Bdim", "diminished"),
        ("Caug", "augmented"),
        ("Dsus2", "suspended"),
        ("E", "major"),
        ("F7", "major"),
    ],
)
def test_parse_chord_quality_parametrized(chord: str, expected_quality: str) -> None:
    assert music_theory._parse_chord_quality(chord) == expected_quality
