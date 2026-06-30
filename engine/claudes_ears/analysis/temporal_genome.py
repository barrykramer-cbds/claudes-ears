"""Temporal genome view: era/genre clustering from genome map and caller-supplied metadata."""

from __future__ import annotations

import math
from typing import cast

import numpy as np

from claudes_ears._sanitize import sanitize


def _empty_result() -> dict[str, object]:
    return {
        "tracks": [],
        "eras": {},
        "genre_clusters": {},
        "temporal_correlation": None,
        "cross_era_twins": [],
    }


def analyze(
    genome_map: dict[str, object], metadata: dict[str, dict[str, object]]
) -> dict[str, object]:
    """Cluster tracks by era/genre; metadata is {track_id: {year, genre, era, artist, ...}}."""
    distances = cast("dict[str, float]", genome_map.get("distances_from_center") or {})
    if not distances:
        return cast("dict[str, object]", sanitize(_empty_result()))

    tracks: list[dict[str, object]] = []
    for name, dist in distances.items():
        meta = metadata.get(name) or {}
        tracks.append(
            {
                "name": name,
                "distance": dist,
                "year": int(cast("int | None", meta.get("year")) or 0),
                "artist": str(meta.get("artist") or "Unknown"),
                "genre": str(meta.get("genre") or "unknown"),
                "era": str(meta.get("era") or "unknown"),
            }
        )
    tracks.sort(key=lambda t: cast("int", t["year"]))

    eras: dict[str, list[str]] = {}
    for t in tracks:
        era = cast("str", t["era"])
        eras.setdefault(era, []).append(cast("str", t["name"]))

    genre_clusters: dict[str, list[str]] = {}
    for t in tracks:
        genre = cast("str", t["genre"])
        genre_clusters.setdefault(genre, []).append(cast("str", t["name"]))

    temporal_corr: float | None = None
    dated = [
        (cast("int", t["year"]), cast("float", t["distance"]))
        for t in tracks
        if cast("int", t["year"]) > 0
    ]
    if len(dated) > 3:
        years = [x[0] for x in dated]
        dists = [x[1] for x in dated]
        corr = float(np.corrcoef(years, dists)[0, 1])
        if math.isfinite(corr):
            temporal_corr = round(corr, 4)

    similar_pairs = cast("list[dict[str, object]]", genome_map.get("most_similar_pairs") or [])
    cross_era_twins: list[dict[str, object]] = []
    for p in similar_pairs[:10]:
        pair_str = str(p.get("pair") or "")
        parts = pair_str.split(" <-> ")
        if len(parts) != 2:
            continue
        a_meta = metadata.get(parts[0]) or {}
        b_meta = metadata.get(parts[1]) or {}
        a_era = str(a_meta.get("era") or "unknown")
        b_era = str(b_meta.get("era") or "unknown")
        a_year = int(cast("int | None", a_meta.get("year")) or 0)
        b_year = int(cast("int | None", b_meta.get("year")) or 0)
        if a_era != b_era and a_year > 0 and b_year > 0:
            cross_era_twins.append(
                {
                    "similarity": p.get("similarity"),
                    "track_a": parts[0],
                    "year_a": a_year,
                    "track_b": parts[1],
                    "year_b": b_year,
                    "year_gap": abs(a_year - b_year),
                }
            )

    result: dict[str, object] = {
        "tracks": tracks,
        "eras": eras,
        "genre_clusters": genre_clusters,
        "temporal_correlation": temporal_corr,
        "cross_era_twins": cross_era_twins,
    }
    return cast("dict[str, object]", sanitize(result))
