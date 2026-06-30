"""genome_map.analyze: cross-track feature vectors, pairwise similarity, collection stats."""

from __future__ import annotations

from claudes_ears.analysis import genome_map

_REQUIRED_KEYS = {
    "track_count",
    "genome",
    "most_similar_pairs",
    "most_different_pairs",
    "neighbors",
    "most_typical_track",
    "most_unique_track",
    "distances_from_center",
}


def _stem(
    *,
    pitch: float = 200.0,
    tempo: float = 120.0,
    track_id: str | None = None,
) -> dict[str, object]:
    base: dict[str, object] = {
        "vocals": {"pitch_mean_hz": pitch, "breathiness": 0.3, "voiced_fraction": 0.8},
        "drums": {
            "tempo_bpm": tempo,
            "onsets_per_second": 4.0,
            "beat_regularity": 0.9,
            "kit_balance": {"kick": 0.4},
        },
        "bass": {"root_movement_rate": 0.5},
        "other": {"centroid_hz": 3000.0, "harmonic_pct": 0.7},
    }
    if track_id is not None:
        base["id"] = track_id
    return base


def test_empty_list_returns_degraded_contract() -> None:
    result = genome_map.analyze([])
    assert set(result) >= _REQUIRED_KEYS
    assert result["track_count"] == 0
    assert result["genome"] == {}
    assert result["most_similar_pairs"] == []
    assert result["distances_from_center"] == {}


def test_single_track_returns_degraded_contract() -> None:
    result = genome_map.analyze([_stem()])
    assert set(result) >= _REQUIRED_KEYS
    assert result["track_count"] == 1
    assert result["most_similar_pairs"] == []


def test_two_tracks_emit_full_contract() -> None:
    result = genome_map.analyze([_stem(pitch=200.0, tempo=120.0), _stem(pitch=400.0, tempo=90.0)])
    assert set(result) >= _REQUIRED_KEYS
    assert result["track_count"] == 2
    pairs = result["most_similar_pairs"]
    assert isinstance(pairs, list)
    assert len(pairs) == 1
    assert isinstance(pairs[0]["similarity"], float)


def test_track_ids_used_as_neighbor_keys_when_present() -> None:
    stems = [_stem(track_id="alpha"), _stem(track_id="beta")]
    result = genome_map.analyze(stems)
    dists = result["distances_from_center"]
    assert isinstance(dists, dict)
    assert "alpha" in dists
    assert "beta" in dists


def test_index_fallback_when_no_id_field() -> None:
    result = genome_map.analyze([_stem(), _stem()])
    dists = result["distances_from_center"]
    assert isinstance(dists, dict)
    assert "0" in dists
    assert "1" in dists


def test_genome_stats_contain_mean_and_std() -> None:
    stems = [_stem(pitch=200.0), _stem(pitch=400.0)]
    result = genome_map.analyze(stems)
    genome = result["genome"]
    assert isinstance(genome, dict)
    assert len(genome) > 0
    first_stats = next(iter(genome.values()))
    assert isinstance(first_stats, dict)
    assert "mean" in first_stats
    assert "std" in first_stats


def test_missing_stem_fields_do_not_raise() -> None:
    """Sparse dicts (missing vocals/drums keys) must not raise."""
    result = genome_map.analyze([{}, {}])
    assert set(result) >= _REQUIRED_KEYS
    assert result["track_count"] == 2


def test_most_typical_and_unique_track_identified() -> None:
    stems = [
        _stem(pitch=200.0, tempo=120.0),
        _stem(pitch=200.0, tempo=121.0),
        _stem(pitch=800.0, tempo=200.0),
    ]
    result = genome_map.analyze(stems)
    assert result["most_typical_track"] is not None
    assert result["most_unique_track"] is not None
    typical = result["most_typical_track"]
    assert isinstance(typical, dict)
    assert "name" in typical
    assert "distance" in typical
