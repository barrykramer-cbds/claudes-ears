"""Consolidator: degraded domains null (not raise), genome extraction, discriminators."""

from __future__ import annotations

from datetime import UTC, datetime
import math

from claudes_ears.models.perception import GenomeVector, TrackMeta
from claudes_ears.pipeline.consolidator import consolidate

_STEM_ANALYSIS = {
    "vocals": {
        "duration": 1.0,
        "pitch_mean_hz": 220.0,
        "pitch_range_semitones": 12.0,
        "voiced_fraction": 0.8,
        "vocal_melodic_entropy": 2.5,
        "breathiness": 0.3,
        "breathiness_desc": "soft",
        "dynamic_range_db": 10.0,
    },
    "drums": {
        "duration": 1.0,
        "tempo_bpm": 120.0,
        "onsets_per_second": 4.0,
        "beat_regularity": 0.9,
        "kit_balance": {"kick": 0.4, "snare": 0.3, "hihat": 0.3},
    },
    "bass": {
        "duration": 1.0,
        "dominant_notes": ["E"],
        "root_movement_rate": 0.5,
        "root_movement_desc": "walking",
    },
    "other": {
        "duration": 1.0,
        "centroid_hz": 2000.0,
        "bandwidth_hz": 1000.0,
        "texture": "lush",
        "harmonic_pct": 0.6,
        "attack": "soft",
    },
}


def _meta() -> TrackMeta:
    return TrackMeta(
        id="track",
        source_path="/songs/x.mp3",
        analyzed_at=datetime.now(UTC),
        pipeline_version="0.1.0",
    )


def test_empty_results_null_every_domain_without_raising() -> None:
    doc = consolidate(_meta(), {})
    for domain in ("stems", "vocals", "harmony", "emotion", "spatial", "genome"):
        assert getattr(doc, domain) is None


def test_degraded_step_nulls_only_its_subfield() -> None:
    """A present chord dict survives even when its sibling derived steps are missing."""
    chords = {"tempo": 120.0, "total_beats": 4, "total_segments": 1, "unique_chords": 1}
    doc = consolidate(_meta(), {"chord_progression": chords})
    assert doc.harmony is not None
    assert doc.harmony.chords is not None
    assert doc.harmony.theory is None


def test_genome_vector_is_twelve_finite_floats() -> None:
    doc = consolidate(_meta(), {"analyze_stems": _STEM_ANALYSIS})
    assert isinstance(doc.genome, GenomeVector)
    dims = doc.genome.as_list()
    assert len(dims) == len(GenomeVector.DIMS)
    assert all(isinstance(value, float) and math.isfinite(value) for value in dims)


def test_genome_null_when_a_dimension_is_missing() -> None:
    """A dim absent from the stem dict (here drum beat_regularity) collapses the vector."""
    drums = {
        key: value for key, value in _STEM_ANALYSIS["drums"].items() if key != "beat_regularity"
    }
    doc = consolidate(_meta(), {"analyze_stems": {**_STEM_ANALYSIS, "drums": drums}})
    assert doc.genome is None


def test_genome_null_when_a_dimension_is_nonfinite() -> None:
    """Non-finite source value sanitizes to None, collapsing the all-or-nothing vector."""
    stems = {**_STEM_ANALYSIS, "vocals": {**_STEM_ANALYSIS["vocals"], "pitch_mean_hz": math.inf}}
    doc = consolidate(_meta(), {"analyze_stems": stems})
    assert doc.genome is None


def test_harmonic_rhythm_degenerate_window_key_is_normalized() -> None:
    results = {
        "harmonic_rhythm": {
            "total_changes": 2,
            "harmonic_rhythm_windows": [
                {
                    "time": 0.0,
                    "label": "0:00",
                    "changes": 1,
                    "changes_per_beat": 0.5,
                    "changes_per_bar": 2.0,
                    "avg_interval_s": 1.0,
                    "rhythm_class": "moderate",
                    "narrative": "steady",
                }
            ],
        }
    }
    doc = consolidate(_meta(), results)
    assert doc.harmony is not None
    assert doc.harmony.harmonic_rhythm is not None
    assert len(doc.harmony.harmonic_rhythm.windows) == 1


def test_emotion_error_variant_nulls_the_domain() -> None:
    doc = consolidate(_meta(), {"emotional_trajectory": {"error": "too short"}})
    assert doc.emotion is None


def test_music_theory_numerals_are_sorted() -> None:
    results = {
        "music_theory": {
            "key": "C",
            "mode": "major",
            "total_chords": 3,
            "harmonic_vocabulary_size": 3,
            "chromatic_chords_pct": 0.0,
            "total_cadences": 0,
            "unique_numerals": ["V", "I", "IV"],
        }
    }
    doc = consolidate(_meta(), results)
    assert doc.harmony is not None
    assert doc.harmony.theory is not None
    assert doc.harmony.theory.unique_numerals == ["I", "IV", "V"]


def test_structure_empty_narrative_collapses_to_none() -> None:
    doc = consolidate(_meta(), {"temporal_segmentation": {"snapshots": [], "narrative": {}}})
    assert doc.structure is not None
    assert doc.structure.narrative is None
