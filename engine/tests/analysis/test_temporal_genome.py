"""temporal_genome.analyze: era/genre clustering; no hardcoded metadata (ISSUE-014)."""

from __future__ import annotations

from claudes_ears.analysis import temporal_genome

_REQUIRED_KEYS = {"tracks", "eras", "genre_clusters", "temporal_correlation", "cross_era_twins"}

_GENOME_MAP: dict[str, object] = {
    "distances_from_center": {
        "track_a": 0.5,
        "track_b": 1.2,
        "track_c": 0.8,
    },
    "most_similar_pairs": [
        {"pair": "track_a <-> track_b", "similarity": 0.91},
        {"pair": "track_b <-> track_c", "similarity": 0.75},
    ],
}

_METADATA: dict[str, dict[str, object]] = {
    "track_a": {"year": 1975, "artist": "Queen", "genre": "rock opera", "era": "1970s"},
    "track_b": {"year": 2013, "artist": "Eminem", "genre": "hip-hop", "era": "2010s"},
    "track_c": {"year": 2006, "artist": "Amy Winehouse", "genre": "soul/R&B", "era": "2000s"},
}


def test_full_contract_keys_present() -> None:
    result = temporal_genome.analyze(_GENOME_MAP, _METADATA)
    assert set(result) >= _REQUIRED_KEYS


def test_tracks_sorted_by_year() -> None:
    result = temporal_genome.analyze(_GENOME_MAP, _METADATA)
    tracks = result["tracks"]
    assert isinstance(tracks, list)
    years = [int(t["year"]) for t in tracks]
    assert years == sorted(years)


def test_era_grouping_uses_metadata_not_hardcoded_values() -> None:
    """ISSUE-014: era comes from the metadata param, not module constants."""
    custom_meta: dict[str, dict[str, object]] = {
        "track_a": {"year": 1975, "artist": "X", "genre": "rock", "era": "classic"},
        "track_b": {"year": 2013, "artist": "Y", "genre": "rap", "era": "modern"},
        "track_c": {"year": 2006, "artist": "Z", "genre": "soul", "era": "modern"},
    }
    result = temporal_genome.analyze(_GENOME_MAP, custom_meta)
    eras = result["eras"]
    assert isinstance(eras, dict)
    assert "classic" in eras
    assert "modern" in eras
    assert "1970s" not in eras  # not from any hardcoded fallback


def test_genre_clusters_built_from_metadata() -> None:
    result = temporal_genome.analyze(_GENOME_MAP, _METADATA)
    clusters = result["genre_clusters"]
    assert isinstance(clusters, dict)
    assert "hip-hop" in clusters
    assert "rock opera" in clusters


def test_cross_era_twins_detected() -> None:
    result = temporal_genome.analyze(_GENOME_MAP, _METADATA)
    twins = result["cross_era_twins"]
    assert isinstance(twins, list)
    # track_a (1970s) vs track_b (2010s) are the most similar pair and cross-era
    assert any(t["track_a"] == "track_a" and t["track_b"] == "track_b" for t in twins)


def test_empty_genome_map_returns_degraded_contract() -> None:
    result = temporal_genome.analyze({}, {})
    assert set(result) >= _REQUIRED_KEYS
    assert result["tracks"] == []
    assert result["temporal_correlation"] is None


def test_missing_metadata_falls_back_gracefully() -> None:
    """Tracks with no metadata entry get Unknown/unknown defaults, not an exception."""
    result = temporal_genome.analyze(_GENOME_MAP, {})
    tracks = result["tracks"]
    assert isinstance(tracks, list)
    assert len(tracks) == 3
    for t in tracks:
        assert t["artist"] == "Unknown"
        assert t["genre"] == "unknown"


def test_temporal_correlation_absent_for_too_few_dated_tracks() -> None:
    # Only 2 tracks with valid years -> correlation not computed (needs >3)
    small_map: dict[str, object] = {
        "distances_from_center": {"a": 0.5, "b": 1.0},
        "most_similar_pairs": [],
    }
    meta: dict[str, dict[str, object]] = {
        "a": {"year": 1990, "era": "1990s"},
        "b": {"year": 2010, "era": "2010s"},
    }
    result = temporal_genome.analyze(small_map, meta)
    assert result["temporal_correlation"] is None
