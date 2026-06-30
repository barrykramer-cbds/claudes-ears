"""story_reader.analyze: output contract, degraded inputs, ISSUE-008 safe access."""

from __future__ import annotations

from claudes_ears.analysis import story_reader

_REQUIRED_KEYS = {
    "total_moments",
    "key",
    "mode",
    "tempo",
    "dominant_chord_patterns",
    "story_moments",
    "arc_narrative",
}

_MOMENT_KEYS = {
    "start",
    "end",
    "duration_s",
    "emotional_state",
    "energy",
    "tension_trend",
    "vocal_relationship",
    "chord",
    "vessel_description",
}


def _make_deps(
    vocal_relationships: object = None,
    emotional_trajectory: object = None,
    music_theory: object = None,
    chord_progression: object = None,
    temporal_segmentation: object = None,
) -> dict[str, object]:
    return {
        "vocal_relationships": vocal_relationships,
        "emotional_trajectory": emotional_trajectory,
        "music_theory": music_theory,
        "chord_progression": chord_progression,
        "temporal_segmentation": temporal_segmentation,
    }


def test_all_deps_none_returns_full_contract() -> None:
    """ISSUE-008: None deps must not raise — must return full schema."""
    result = story_reader.analyze(_make_deps())
    assert set(result) >= _REQUIRED_KEYS
    assert result["total_moments"] == 0
    assert result["story_moments"] == []
    assert result["key"] is None
    assert result["mode"] is None


def test_all_deps_empty_dict_returns_full_contract() -> None:
    """ISSUE-008: empty dicts for every dep must not crash."""
    result = story_reader.analyze(
        _make_deps(
            vocal_relationships={},
            emotional_trajectory={},
            music_theory={},
            chord_progression={},
            temporal_segmentation={},
        )
    )
    assert set(result) >= _REQUIRED_KEYS
    assert result["total_moments"] == 0


def test_error_dict_dep_handled_safely() -> None:
    """ISSUE-008: upstream error objects must not cause KeyError or crash."""
    error_emotion = {"error": "No temporal snapshots found"}
    result = story_reader.analyze(_make_deps(emotional_trajectory=error_emotion))
    assert set(result) >= _REQUIRED_KEYS
    assert result["total_moments"] == 0


def test_partial_deps_theory_only() -> None:
    theory = {"key": "G", "mode": "major", "cadences": [], "analyzed_chords": []}
    result = story_reader.analyze(_make_deps(music_theory=theory))
    assert result["key"] == "G"
    assert result["mode"] == "major"
    assert result["total_moments"] == 0


def test_emotional_phases_become_story_moments() -> None:
    phases = [
        {
            "state": "gentle presence",
            "energy": "moderate",
            "start": "0:00",
            "end": "0:30",
            "duration_s": 30.0,
            "tension_trend": "steady",
            "avg_tension": 0.001,
            "avg_warmth": 1.6,
        },
        {
            "state": "cold tension",
            "energy": "strong",
            "start": "0:30",
            "end": "1:00",
            "duration_s": 30.0,
            "tension_trend": "rising",
            "avg_tension": 0.005,
            "avg_warmth": 1.0,
        },
    ]
    emotional = {
        "total_phases": 2,
        "phases": phases,
        "narrative": "Opens in gentle presence at moderate energy",
    }
    result = story_reader.analyze(_make_deps(emotional_trajectory=emotional))
    assert result["total_moments"] == 2
    moments = result["story_moments"]
    assert isinstance(moments, list)
    first = moments[0]
    assert isinstance(first, dict)
    assert set(first) >= _MOMENT_KEYS
    assert first["emotional_state"] == "gentle presence"
    assert first["energy"] == "moderate"


def test_chord_context_injected_into_moments() -> None:
    phases = [
        {
            "state": "gentle presence",
            "energy": "moderate",
            "start": 10.0,
            "end": 30.0,
            "duration_s": 20.0,
            "tension_trend": "steady",
            "avg_tension": 0.001,
            "avg_warmth": 1.5,
        },
    ]
    chord_segs = [
        {"chord": "Am", "start": 0.0, "end": 20.0},
        {"chord": "G", "start": 20.0, "end": 40.0},
    ]
    result = story_reader.analyze(
        _make_deps(
            emotional_trajectory={"phases": phases},
            chord_progression={"segments": chord_segs, "top_patterns": [], "tempo": 120.0},
        )
    )
    moments = result["story_moments"]
    assert isinstance(moments, list)
    assert len(moments) == 1
    assert moments[0]["chord"] == "Am"


def test_vocal_relationship_injected_into_moments() -> None:
    phases = [
        {
            "state": "deep peace",
            "energy": "quiet",
            "start": "0:05",
            "end": "0:30",
            "duration_s": 25.0,
            "tension_trend": "steady",
            "avg_tension": 0.0005,
            "avg_warmth": 2.0,
        },
    ]
    vr_moments = [
        {"time": 5.0, "relationship": "solo"},
        {"time": 20.0, "relationship": "support"},
    ]
    result = story_reader.analyze(
        _make_deps(
            emotional_trajectory={"phases": phases},
            vocal_relationships={"moments": vr_moments},
        )
    )
    moments = result["story_moments"]
    assert isinstance(moments, list)
    assert moments[0]["vocal_relationship"] == "solo"


def test_vessel_description_non_empty_with_context() -> None:
    phases = [
        {
            "state": "cold tension",
            "energy": "strong",
            "start": "0:00",
            "end": "0:20",
            "duration_s": 20.0,
            "tension_trend": "rising",
            "avg_tension": 0.005,
            "avg_warmth": 1.0,
        },
    ]
    result = story_reader.analyze(
        _make_deps(
            emotional_trajectory={"phases": phases},
        )
    )
    moments = result["story_moments"]
    assert isinstance(moments, list)
    desc = str(moments[0].get("vessel_description", ""))
    assert len(desc) > 0


def test_arc_narrative_includes_theory_key() -> None:
    phases = [
        {
            "state": "neutral flow",
            "energy": "moderate",
            "start": "0:00",
            "end": "0:30",
            "duration_s": 30.0,
            "tension_trend": "steady",
            "avg_tension": 0.002,
            "avg_warmth": 1.5,
        },
    ]
    result = story_reader.analyze(
        _make_deps(
            emotional_trajectory={"phases": phases, "narrative": "Opens in neutral flow"},
            music_theory={"key": "D", "mode": "minor"},
        )
    )
    arc = str(result.get("arc_narrative", ""))
    assert "D" in arc
    assert "minor" in arc


def test_dominant_chord_patterns_from_top_patterns() -> None:
    top = [
        {"pattern": "C -> Am -> F -> G", "count": 8},
        {"pattern": "Am -> F -> C -> G", "count": 5},
    ]
    result = story_reader.analyze(
        _make_deps(
            chord_progression={"segments": [], "top_patterns": top, "tempo": 100.0},
        )
    )
    patterns = result["dominant_chord_patterns"]
    assert isinstance(patterns, list)
    assert "C -> Am -> F -> G" in patterns


def test_non_dict_phases_skipped_safely() -> None:
    """Non-dict entries in phases list must not raise."""
    emotional = {
        "phases": [
            None,
            "bad",
            42,
            {
                "state": "neutral flow",
                "energy": "quiet",
                "start": "0:00",
                "end": "0:10",
                "duration_s": 10.0,
                "tension_trend": "steady",
                "avg_tension": 0.001,
                "avg_warmth": 1.0,
            },
        ]
    }
    result = story_reader.analyze(_make_deps(emotional_trajectory=emotional))
    assert result["total_moments"] == 1
