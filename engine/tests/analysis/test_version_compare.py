"""version_compare.analyze: producer-fingerprint deltas between two PerceptionDocuments."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from claudes_ears.analysis import version_compare
from claudes_ears.models.perception import (
    DepthReverb,
    DrumsStem,
    EmotionTrajectory,
    GrooveTiming,
    KitBalance,
    PerceptionDocument,
    RhythmAnalysis,
    SpatialAnalysis,
    StemAnalysis,
    TrackMeta,
    VocalsStem,
)

_REQUIRED_KEYS = {"version_a", "version_b", "deltas", "fingerprint_top_changes"}


def _doc(
    track_id: str = "test",
    *,
    stems: StemAnalysis | None = None,
    rhythm: RhythmAnalysis | None = None,
    spatial: SpatialAnalysis | None = None,
    emotion: EmotionTrajectory | None = None,
) -> PerceptionDocument:
    return PerceptionDocument(
        track=TrackMeta(
            id=track_id,
            source_path=f"/tmp/{track_id}.mp3",
            analyzed_at=datetime(2026, 1, 1, tzinfo=UTC),
            pipeline_version="1.0",
        ),
        stems=stems,
        rhythm=rhythm,
        spatial=spatial,
        emotion=emotion,
    )


def _vocals_stem(pitch: float = 200.0, breathiness: float = 0.3) -> VocalsStem:
    return VocalsStem(
        duration=180.0,
        breathiness=breathiness,
        breathiness_desc="light",
        dynamic_range_db=12.0,
        pitch_mean_hz=pitch,
    )


def _drums_stem(tempo: float = 120.0) -> DrumsStem:
    return DrumsStem(
        duration=180.0,
        tempo_bpm=tempo,
        onsets_per_second=4.0,
        kit_balance=KitBalance(kick=0.4, snare=0.35, hihat=0.25),
    )


def test_minimal_docs_emit_required_keys() -> None:
    result = version_compare.analyze(_doc("a"), _doc("b"))
    assert set(result) >= _REQUIRED_KEYS
    assert result["version_a"] == {"id": "a", "title": None}
    assert result["version_b"] == {"id": "b", "title": None}


def test_no_domains_produces_empty_deltas() -> None:
    result = version_compare.analyze(_doc("a"), _doc("b"))
    assert result["deltas"] == {}
    assert result["fingerprint_top_changes"] == []


def test_vocal_stem_delta_computed() -> None:
    doc_a = _doc("a", stems=StemAnalysis(vocals=_vocals_stem(pitch=200.0)))
    doc_b = _doc("b", stems=StemAnalysis(vocals=_vocals_stem(pitch=300.0)))
    result = version_compare.analyze(doc_a, doc_b)
    deltas = result["deltas"]
    assert isinstance(deltas, dict)
    assert "vocals" in deltas
    pitch_d = deltas["vocals"]["pitch_mean_hz"]
    assert pitch_d is not None
    assert pitch_d["delta"] == pytest.approx(100.0)
    assert pitch_d["pct_change"] == pytest.approx(50.0)


def test_breathiness_delta_with_equal_values() -> None:
    stem = StemAnalysis(vocals=_vocals_stem(breathiness=0.5))
    result = version_compare.analyze(_doc("a", stems=stem), _doc("b", stems=stem))
    brd = result["deltas"]["vocals"]["breathiness"]  # type: ignore[index]
    assert brd is not None
    assert brd["delta"] == 0.0


def test_drums_delta_computed() -> None:
    doc_a = _doc("a", stems=StemAnalysis(drums=_drums_stem(tempo=120.0)))
    doc_b = _doc("b", stems=StemAnalysis(drums=_drums_stem(tempo=100.0)))
    result = version_compare.analyze(doc_a, doc_b)
    deltas = result["deltas"]
    assert isinstance(deltas, dict)
    assert "drums" in deltas
    tempo_d = deltas["drums"]["tempo_bpm"]
    assert tempo_d["delta"] == pytest.approx(-20.0)


def test_missing_domain_in_one_doc_skips_delta() -> None:
    """If only one doc has stems, the stems delta section is omitted."""
    doc_a = _doc("a", stems=StemAnalysis(vocals=_vocals_stem()))
    doc_b = _doc("b")
    result = version_compare.analyze(doc_a, doc_b)
    deltas = result["deltas"]
    assert isinstance(deltas, dict)
    assert "vocals" not in deltas


def test_groove_feel_label_delta() -> None:
    groove_a = GrooveTiming(duration=180.0, tempo=120.0, beat_count=360, feel="laid-back")
    groove_b = GrooveTiming(duration=180.0, tempo=120.0, beat_count=360, feel="driving")
    doc_a = _doc("a", rhythm=RhythmAnalysis(groove=groove_a))
    doc_b = _doc("b", rhythm=RhythmAnalysis(groove=groove_b))
    result = version_compare.analyze(doc_a, doc_b)
    feel = result["deltas"]["groove"]["feel_change"]  # type: ignore[index]
    assert feel is not None
    assert feel["changed"] is True
    assert feel["version_a"] == "laid-back"


def test_depth_reverb_delta() -> None:
    depth_a = DepthReverb(
        duration=180.0,
        rt60_estimate=0.8,
        pre_delay_ms=10.0,
        spectral_persistence=0.6,
        spectral_flatness_mean=0.3,
        spectral_flatness_std=0.05,
        wetness_index=0.4,
        room_size="medium",
        perceived_distance="near",
        spatial_placement="center",
    )
    depth_b = DepthReverb(
        duration=180.0,
        rt60_estimate=2.0,
        pre_delay_ms=40.0,
        spectral_persistence=0.9,
        spectral_flatness_mean=0.5,
        spectral_flatness_std=0.1,
        wetness_index=0.8,
        room_size="large",
        perceived_distance="far",
        spatial_placement="rear",
    )
    doc_a = _doc("a", spatial=SpatialAnalysis(depth=depth_a))
    doc_b = _doc("b", spatial=SpatialAnalysis(depth=depth_b))
    result = version_compare.analyze(doc_a, doc_b)
    deltas = result["deltas"]
    assert isinstance(deltas, dict)
    assert "depth" in deltas
    wet = deltas["depth"]["wetness_index"]
    assert wet["delta"] == pytest.approx(0.4, abs=1e-4)


def test_fingerprint_top_changes_sorted_by_pct_magnitude() -> None:
    doc_a = _doc(
        "a",
        stems=StemAnalysis(
            vocals=_vocals_stem(pitch=100.0),
            drums=_drums_stem(tempo=120.0),
        ),
    )
    doc_b = _doc(
        "b",
        stems=StemAnalysis(
            vocals=_vocals_stem(pitch=300.0),  # +200%
            drums=_drums_stem(tempo=124.0),  # +3.3%
        ),
    )
    result = version_compare.analyze(doc_a, doc_b)
    top = result["fingerprint_top_changes"]
    assert isinstance(top, list)
    assert len(top) > 0
    pcts = [abs(float(c["pct_change"])) for c in top]
    assert pcts == sorted(pcts, reverse=True)
    # Largest single change is pitch (+200%)
    assert top[0]["metric"] == "pitch_mean_hz"


def test_emotion_delta() -> None:
    emo_a = EmotionTrajectory(
        total_windows=10,
        total_transitions=4,
        total_phases=3,
        unique_states=3,
        narrative="arc",
    )
    emo_b = EmotionTrajectory(
        total_windows=10,
        total_transitions=8,
        total_phases=5,
        unique_states=4,
        narrative="arc",
    )
    result = version_compare.analyze(_doc("a", emotion=emo_a), _doc("b", emotion=emo_b))
    deltas = result["deltas"]
    assert isinstance(deltas, dict)
    assert "emotion" in deltas
    tr = deltas["emotion"]["total_transitions"]
    assert tr["delta"] == pytest.approx(4.0)
