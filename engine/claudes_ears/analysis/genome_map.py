"""Cross-track genome: pairwise similarity and collection-wide feature stats."""

from __future__ import annotations

from typing import cast

import numpy as np

from claudes_ears._sanitize import sanitize

_DIMS: tuple[str, ...] = (
    "vocal_pitch",
    "vocal_range",
    "vocal_entropy",
    "vocal_breathiness",
    "vocal_presence",
    "drum_tempo",
    "drum_regularity",
    "drum_density",
    "drum_kick_pct",
    "bass_movement",
    "texture_centroid",
    "texture_harmonic",
)


def _getf(d: dict[str, object], key: str) -> float:
    """Extract a numeric value as float; returns 0.0 for missing or non-numeric."""
    val = d.get(key)
    return float(val) if isinstance(val, (int, float)) and not isinstance(val, bool) else 0.0


def _extract_vector(stem: dict[str, object]) -> dict[str, float]:
    v = cast("dict[str, object]", stem.get("vocals") or {})
    d = cast("dict[str, object]", stem.get("drums") or {})
    b = cast("dict[str, object]", stem.get("bass") or {})
    o = cast("dict[str, object]", stem.get("other") or {})
    kit = cast("dict[str, object]", d.get("kit_balance") or {})
    return {
        "vocal_pitch": _getf(v, "pitch_mean_hz"),
        "vocal_range": _getf(v, "pitch_range_semitones"),
        "vocal_entropy": _getf(v, "vocal_melodic_entropy"),
        "vocal_breathiness": _getf(v, "breathiness"),
        "vocal_presence": _getf(v, "voiced_fraction"),
        "drum_tempo": _getf(d, "tempo_bpm"),
        "drum_regularity": _getf(d, "beat_regularity"),
        "drum_density": _getf(d, "onsets_per_second"),
        "drum_kick_pct": _getf(kit, "kick"),
        "bass_movement": _getf(b, "root_movement_rate"),
        "texture_centroid": _getf(o, "centroid_hz"),
        "texture_harmonic": _getf(o, "harmonic_pct"),
    }


def _cosine_sim(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Scale-normalized cosine similarity — each dim divided by its local max."""
    keys = sorted(set(vec_a) & set(vec_b))
    a = np.array([vec_a[k] for k in keys], dtype=np.float64)
    b = np.array([vec_b[k] for k in keys], dtype=np.float64)
    for i in range(len(a)):
        mx = max(abs(float(a[i])), abs(float(b[i])), 1e-10)
        a[i] /= mx
        b[i] /= mx
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na > 0 and nb > 0:
        return round(float(np.dot(a, b) / (na * nb)), 4)
    return 0.0


def _empty_result(track_count: int = 0) -> dict[str, object]:
    return {
        "track_count": track_count,
        "genome": {},
        "most_similar_pairs": [],
        "most_different_pairs": [],
        "neighbors": {},
        "most_typical_track": None,
        "most_unique_track": None,
        "distances_from_center": {},
    }


def analyze(stem_analyses: list[dict[str, object]]) -> dict[str, object]:
    """Compute cross-track genome stats from per-track analyze_stems result dicts."""
    if len(stem_analyses) < 2:
        return cast("dict[str, object]", sanitize(_empty_result(len(stem_analyses))))

    # Prefer "id" field for track identity; fall back to list index
    names = [str(s.get("id") or i) for i, s in enumerate(stem_analyses)]
    vectors = {name: _extract_vector(stem) for name, stem in zip(names, stem_analyses, strict=True)}
    name_list = list(vectors)

    pairs: list[tuple[str, float]] = []
    for i in range(len(name_list)):
        for j in range(i + 1, len(name_list)):
            sim = _cosine_sim(vectors[name_list[i]], vectors[name_list[j]])
            pairs.append((f"{name_list[i]} <-> {name_list[j]}", sim))
    pairs.sort(key=lambda x: -x[1])

    neighbors: dict[str, list[dict[str, object]]] = {n: [] for n in name_list}
    for pair_label, sim in pairs:
        a, b = pair_label.split(" <-> ", 1)
        neighbors[a].append({"track": b, "similarity": sim})
        neighbors[b].append({"track": a, "similarity": sim})
    for n in neighbors:
        neighbors[n].sort(key=lambda x: -cast("float", x["similarity"]))

    all_vecs = list(vectors.values())
    genome_stats: dict[str, dict[str, object]] = {}
    for dim in _DIMS:
        vals = [v[dim] for v in all_vecs if v[dim] > 0]
        if vals:
            arr = np.array(vals, dtype=np.float64)
            mn, mx = float(np.min(arr)), float(np.max(arr))
            genome_stats[dim] = {
                "mean": round(float(np.mean(arr)), 3),
                "std": round(float(np.std(arr)), 3),
                "min": round(mn, 3),
                "max": round(mx, 3),
                "range_label": f"{mn:.1f} - {mx:.1f}",
            }

    distances: dict[str, float] = {}
    for name, vec in vectors.items():
        dist = 0.0
        for dim, stats in genome_stats.items():
            std = cast("float", stats["std"])
            mean = cast("float", stats["mean"])
            if std > 0:
                dist += ((vec.get(dim, 0.0) - mean) / std) ** 2
        distances[name] = round(float(np.sqrt(dist)), 3)

    most_typical = min(distances, key=distances.__getitem__)
    most_unique = max(distances, key=distances.__getitem__)

    result: dict[str, object] = {
        "track_count": len(stem_analyses),
        "genome": genome_stats,
        "most_similar_pairs": [{"pair": p, "similarity": s} for p, s in pairs[:10]],
        "most_different_pairs": [{"pair": p, "similarity": s} for p, s in pairs[-5:]],
        "neighbors": {k: v[:3] for k, v in neighbors.items()},
        "most_typical_track": {"name": most_typical, "distance": distances[most_typical]},
        "most_unique_track": {"name": most_unique, "distance": distances[most_unique]},
        "distances_from_center": dict(sorted(distances.items(), key=lambda x: x[1])),
    }
    return cast("dict[str, object]", sanitize(result))
