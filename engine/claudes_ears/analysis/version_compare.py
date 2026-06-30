"""Version comparison: producer-fingerprint deltas between two PerceptionDocuments."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from claudes_ears.models.perception import PerceptionDocument


def _delta(a: float | None, b: float | None) -> dict[str, object] | None:
    """Signed delta between two scalar values; None if either is absent."""
    if a is None or b is None:
        return None
    diff = b - a
    pct = (diff / abs(a) * 100.0) if a != 0.0 else 0.0
    return {
        "version_a": round(a, 4),
        "version_b": round(b, 4),
        "delta": round(diff, 4),
        "pct_change": round(pct, 1),
    }


def _label_delta(a: str | None, b: str | None) -> dict[str, object] | None:
    if a is None and b is None:
        return None
    return {"version_a": a, "version_b": b, "changed": a != b}


def analyze(doc_a: PerceptionDocument, doc_b: PerceptionDocument) -> dict[str, object]:
    """Delta two PerceptionDocuments into a producer-fingerprint change report."""
    report: dict[str, object] = {
        "version_a": {"id": doc_a.track.id, "title": doc_a.track.title},
        "version_b": {"id": doc_b.track.id, "title": doc_b.track.title},
        "deltas": {},
        "fingerprint_top_changes": [],
    }
    deltas = cast("dict[str, object]", report["deltas"])

    va = doc_a.stems.vocals if doc_a.stems else None
    vb = doc_b.stems.vocals if doc_b.stems else None
    if va and vb:
        deltas["vocals"] = {
            "pitch_mean_hz": _delta(va.pitch_mean_hz, vb.pitch_mean_hz),
            "pitch_range_semitones": _delta(va.pitch_range_semitones, vb.pitch_range_semitones),
            "vocal_melodic_entropy": _delta(va.vocal_melodic_entropy, vb.vocal_melodic_entropy),
            "breathiness": _delta(va.breathiness, vb.breathiness),
        }

    da = doc_a.stems.drums if doc_a.stems else None
    db = doc_b.stems.drums if doc_b.stems else None
    if da and db:
        deltas["drums"] = {
            "tempo_bpm": _delta(da.tempo_bpm, db.tempo_bpm),
            "beat_regularity": _delta(da.beat_regularity, db.beat_regularity),
            "onsets_per_second": _delta(da.onsets_per_second, db.onsets_per_second),
            "kick_balance": _delta(da.kit_balance.kick, db.kit_balance.kick),
        }

    rel_a = doc_a.vocals.relationships if doc_a.vocals else None
    rel_b = doc_b.vocals.relationships if doc_b.vocals else None
    if rel_a and rel_b:
        rel_types = ("solo", "support", "dialogue", "opposition", "merge", "withdraw")
        deltas["vocal_relationships"] = {
            rt: _delta(
                rel_a.relationship_distribution.get(rt),
                rel_b.relationship_distribution.get(rt),
            )
            for rt in rel_types
        }

    reg_a = doc_a.vocals.register_ if doc_a.vocals else None
    reg_b = doc_b.vocals.register_ if doc_b.vocals else None
    if reg_a and reg_b:
        span_a = reg_a.singer_range_high - reg_a.singer_range_low
        span_b = reg_b.singer_range_high - reg_b.singer_range_low
        reg_types = ("chest", "head", "falsetto", "fry")
        deltas["register"] = {
            "pitch_span": _delta(span_a, span_b),
            "total_transitions": _delta(
                float(reg_a.total_transitions), float(reg_b.total_transitions)
            ),
            **{
                rt: _delta(
                    reg_a.register_distribution.get(rt),
                    reg_b.register_distribution.get(rt),
                )
                for rt in reg_types
            },
        }

    depth_a = doc_a.spatial.depth if doc_a.spatial else None
    depth_b = doc_b.spatial.depth if doc_b.spatial else None
    if depth_a and depth_b:
        deltas["depth"] = {
            "spectral_persistence": _delta(
                depth_a.spectral_persistence, depth_b.spectral_persistence
            ),
            "pre_delay_ms": _delta(depth_a.pre_delay_ms, depth_b.pre_delay_ms),
            "wetness_index": _delta(depth_a.wetness_index, depth_b.wetness_index),
            "spectral_flatness_mean": _delta(
                depth_a.spectral_flatness_mean, depth_b.spectral_flatness_mean
            ),
        }

    groove_a = doc_a.rhythm.groove if doc_a.rhythm else None
    groove_b = doc_b.rhythm.groove if doc_b.rhythm else None
    if groove_a and groove_b:
        deltas["groove"] = {
            "mean_deviation_ms": _delta(groove_a.mean_deviation_ms, groove_b.mean_deviation_ms),
            "swing_ratio": _delta(groove_a.swing_ratio, groove_b.swing_ratio),
            "feel_change": _label_delta(groove_a.feel, groove_b.feel),
        }

    hr_a = doc_a.harmony.harmonic_rhythm if doc_a.harmony else None
    hr_b = doc_b.harmony.harmonic_rhythm if doc_b.harmony else None
    if hr_a and hr_b:
        deltas["harmonic_rhythm"] = {
            "avg_changes_per_bar": _delta(hr_a.avg_changes_per_bar, hr_b.avg_changes_per_bar),
            "max_changes_per_bar": _delta(hr_a.max_changes_per_bar, hr_b.max_changes_per_bar),
            "total_accel_events": _delta(
                float(hr_a.total_accel_events) if hr_a.total_accel_events is not None else None,
                float(hr_b.total_accel_events) if hr_b.total_accel_events is not None else None,
            ),
            "arc_change": _label_delta(hr_a.harmonic_arc, hr_b.harmonic_arc),
        }

    emo_a = doc_a.emotion
    emo_b = doc_b.emotion
    if emo_a and emo_b:
        deltas["emotion"] = {
            "total_phases": _delta(float(emo_a.total_phases), float(emo_b.total_phases)),
            "total_transitions": _delta(
                float(emo_a.total_transitions), float(emo_b.total_transitions)
            ),
            "unique_states": _delta(float(emo_a.unique_states), float(emo_b.unique_states)),
        }

    all_changes: list[dict[str, object]] = []
    for category, cat_deltas in cast("dict[str, dict[str, object]]", deltas).items():
        for metric, d in cat_deltas.items():
            if isinstance(d, dict) and "pct_change" in d and d.get("pct_change") is not None:
                all_changes.append(
                    {
                        "category": category,
                        "metric": metric,
                        "delta": d["delta"],
                        "pct_change": d["pct_change"],
                        "version_a": d["version_a"],
                        "version_b": d["version_b"],
                    }
                )
    all_changes.sort(key=lambda x: abs(cast("float", x["pct_change"])), reverse=True)
    report["fingerprint_top_changes"] = all_changes[:10]

    return cast("dict[str, object]", sanitize(report))
