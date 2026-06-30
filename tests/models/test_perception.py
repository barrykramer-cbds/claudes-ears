"""The frozen contract: optionality, variant frames, aliases, genome ordering."""

from datetime import UTC, datetime

from claudes_ears.models.perception import (
    GenomeVector,
    PerceptionDocument,
    RelationshipMoment,
    StereoField,
    TrackMeta,
    VocalRelationships,
)

DOMAINS = (
    "separation",
    "stems",
    "vocals",
    "rhythm",
    "harmony",
    "timbre",
    "spatial",
    "structure",
    "emotion",
    "lyrics",
    "story",
    "ai_detection",
    "genome",
)


def _meta() -> TrackMeta:
    return TrackMeta(
        id="track",
        source_path="/songs/x.mp3",
        analyzed_at=datetime.now(UTC),
        pipeline_version="0.1.0",
    )


def test_every_domain_is_optional_and_defaults_none() -> None:
    """ISSUE-008: a doc with only track meta validates; all domains are None."""
    doc = PerceptionDocument(track=_meta())
    assert doc.schema_version == "1.0"
    for domain in DOMAINS:
        assert getattr(doc, domain) is None


def test_silence_and_full_relationship_frames_share_one_model() -> None:
    """Variant frames (silence drops lead/below/above pct) validate against one model."""
    silence = RelationshipMoment.model_validate(
        {
            "time": 0.0,
            "label": "0:00",
            "relationship": "silence",
            "energy_db": -60,
            "density": 0,
            "density_change": 0,
            "lead_present": False,
            "support_register": "none",
            "narrative": "silence",
        }
    )
    assert silence.lead_pct is None
    full = RelationshipMoment.model_validate(
        {
            "time": 2.0,
            "label": "0:02",
            "relationship": "dialogue",
            "energy_db": -12.5,
            "density": 3,
            "density_change": 1,
            "lead_present": True,
            "lead_pct": 0.6,
            "below_pct": 0.2,
            "above_pct": 0.2,
            "support_register": "head",
            "narrative": "call and response",
        }
    )
    assert full.lead_pct == 0.6


def test_reserved_word_alias_round_trips() -> None:
    rel = VocalRelationships.model_validate(
        {
            "duration": 10.0,
            "lead_pitch_center": 220.0,
            "total_story_phases": 1,
            "total_transitions": 1,
            "transitions": [
                {
                    "time": "0:01",
                    "from": "solo",
                    "to": "dialogue",
                    "from_narrative": "a",
                    "to_narrative": "b",
                }
            ],
        }
    )
    assert rel.transitions[0].from_ == "solo"
    assert rel.model_dump(by_alias=True)["transitions"][0]["from"] == "solo"


def test_mono_stereo_field_validates_with_two_keys() -> None:
    mono = StereoField.model_validate({"stereo": False, "note": "mono source"})
    assert mono.stereo is False
    assert mono.lr_correlation is None


def test_genome_vector_orders_twelve_dims() -> None:
    g = GenomeVector(
        vocal_pitch=1.0,
        vocal_range=2.0,
        vocal_entropy=3.0,
        vocal_breathiness=4.0,
        vocal_presence=5.0,
        drum_tempo=6.0,
        drum_regularity=7.0,
        drum_density=8.0,
        drum_kick_pct=9.0,
        bass_movement=10.0,
        texture_centroid=11.0,
        texture_harmonic=12.0,
    )
    assert g.as_list() == [float(i) for i in range(1, 13)]
    assert "DIMS" not in g.model_dump()
