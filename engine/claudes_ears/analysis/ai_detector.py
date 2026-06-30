"""Structural AI detection: self-opposition (human) vs self-agreement (AI)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, cast

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path


def _sigmoid(x: float, center: float, steepness: float) -> float:
    """Smooth 0-1 score; avoids overflow on extreme inputs."""
    exponent = -steepness * (x - center)
    if exponent > 700:
        return 0.0
    if exponent < -700:
        return 1.0
    return 1.0 / (1.0 + math.exp(exponent))


def _empty_result() -> dict[str, object]:
    """Degraded contract: all required keys present, no vector data."""
    return {
        "overall_score": None,
        "verdict": "INSUFFICIENT DATA (0/7)",
        "confidence": "none",
        "vectors": {},
        "weights": {},
        "vectors_available": 0,
        "vectors_possible": 7,
    }


def _score_relationships(
    rel: dict[str, object],
    vectors: dict[str, dict[str, object]],
    weights: dict[str, float],
) -> None:
    """Populate vectors 1-4 from vocal_relationships output."""
    rd = cast("dict[str, float]", rel.get("relationship_distribution", {}))
    solo = float(rd.get("solo", 0))
    support = float(rd.get("support", 0))
    opposition = float(rd.get("opposition", 0))
    merge = float(rd.get("merge", 0))

    # Low solo → AI-like; human avg 16%, AI avg 5.2%
    v1 = 1.0 - _sigmoid(solo, 10.0, 0.3)
    vectors["solo_pct"] = {
        "value": round(solo, 1),
        "score": round(v1, 3),
        "human_avg": 16.0,
        "ai_avg": 5.2,
        "signal": "low solo suggests AI",
    }
    weights["solo_pct"] = 1.5

    # High support → AI-like; human avg 30.6%, AI avg 54.6%
    v2 = _sigmoid(support, 42.0, 0.12)
    vectors["support_pct"] = {
        "value": round(support, 1),
        "score": round(v2, 3),
        "human_avg": 30.6,
        "ai_avg": 54.6,
        "signal": "high support suggests AI",
    }
    weights["support_pct"] = 1.5

    # Low opposition → AI-like; human avg 2.5%, AI avg 0.8%
    v3 = 1.0 - _sigmoid(opposition, 1.5, 1.5)
    vectors["opposition_pct"] = {
        "value": round(opposition, 1),
        "score": round(v3, 3),
        "human_avg": 2.5,
        "ai_avg": 0.8,
        "signal": "low opposition suggests AI",
    }
    weights["opposition_pct"] = 1.0

    # High merge → AI-like; human avg 1.3%, AI avg 5.5%
    v4 = _sigmoid(merge, 3.0, 0.5)
    vectors["merge_pct"] = {
        "value": round(merge, 1),
        "score": round(v4, 3),
        "human_avg": 1.3,
        "ai_avg": 5.5,
        "signal": "high merge suggests AI",
    }
    weights["merge_pct"] = 0.8


def _score_register(
    reg: dict[str, object],
    vectors: dict[str, dict[str, object]],
    weights: dict[str, float],
) -> None:
    """Populate vectors 5-6 from register_tracking output."""
    span = float(cast("float", reg.get("singer_range_high", 0))) - float(
        cast("float", reg.get("singer_range_low", 0))
    )
    transitions = int(cast("int", reg.get("total_transitions", 0)))
    duration = float(cast("float", reg.get("duration", 1))) or 1.0

    # Narrow pitch span → AI-like; human avg 394 Hz, AI avg 126 Hz
    v5 = 1.0 - _sigmoid(span, 250.0, 0.015)
    vectors["pitch_span_hz"] = {
        "value": round(span, 0),
        "score": round(v5, 3),
        "human_avg": 394,
        "ai_avg": 126,
        "signal": "narrow pitch span suggests AI",
    }
    weights["pitch_span_hz"] = 1.2

    span_octaves = span / 200.0 if span > 0 else 1.0
    trans_per_min = transitions / (duration / 60.0)
    trans_density = trans_per_min / span_octaves

    # Extreme density (noise) or static → AI; human sweet spot 2-8 per min/octave
    if trans_density < 1.0 or trans_density > 15.0:
        v6 = 0.7
    elif trans_density < 2.0 or trans_density > 10.0:
        v6 = 0.4
    else:
        v6 = 0.15

    vectors["register_behavior"] = {
        "value": round(trans_density, 2),
        "score": round(v6, 3),
        "transitions": transitions,
        "span_octaves": round(span_octaves, 2),
        "signal": "extreme transition density suggests AI",
    }
    weights["register_behavior"] = 0.8


def _score_breath(
    breath: dict[str, object],
    stem: dict[str, object],
    vectors: dict[str, dict[str, object]],
    weights: dict[str, float],
) -> None:
    """Populate vector 7 from breath_detection + analyze_stems output."""
    vocals = cast("dict[str, object]", stem.get("vocals", {}))
    breathiness = float(cast("float", vocals.get("breathiness", 0)))
    breath_count = int(cast("int", breath.get("total_breaths", 0)))
    breaths_per_min = float(cast("float", breath.get("breaths_per_minute", 0)))

    # Texture without physiology: high breathiness, zero breath events → AI
    breath_ratio = breaths_per_min / (breathiness * 100) if breathiness > 0.01 else breaths_per_min

    if breath_count == 0 and breathiness > 0.03:
        v7 = 0.9
    elif breath_count == 0 and breathiness > 0.01:
        v7 = 0.6
    elif breath_count == 0:
        v7 = 0.4
    elif breath_ratio < 0.5:
        v7 = 0.5
    else:
        v7 = 0.1

    depth_dist = cast("dict[str, object]", breath.get("depth_distribution", {}))
    deep = int(cast("int", depth_dist.get("deep", 0)))
    if deep > 0:
        # Deep breaths are strong human physiology markers
        v7 *= 0.5

    vectors["breath_physiology"] = {
        "value": round(breath_ratio, 3),
        "score": round(v7, 3),
        "breathiness": round(breathiness, 4),
        "breath_events": breath_count,
        "deep_breaths": deep,
        "signal": "breathiness without breath events suggests AI",
    }
    weights["breath_physiology"] = 2.0


def _verdict(
    overall: float,
    vectors: dict[str, dict[str, object]],
) -> tuple[str, str]:
    """Map overall score + context to a verdict label and confidence tier."""
    if len(vectors) < 4:
        return f"INSUFFICIENT DATA ({len(vectors)}/7)", "none"

    solo_val = float(cast("float", vectors.get("solo_pct", {}).get("value", 50)))
    supp_val = float(cast("float", vectors.get("support_pct", {}).get("value", 0)))
    bp = vectors.get("breath_physiology", {})
    breath_events = int(cast("int", bp.get("breath_events", -1))) if bp else -1
    breathiness_val = float(cast("float", bp.get("breathiness", 0))) if bp else 0.0
    deep_breaths = int(cast("int", bp.get("deep_breaths", 0))) if bp else 0

    heavily_produced = supp_val > 50 and solo_val < 5 and breath_events == 0
    breathiness_paradox = breathiness_val > 0.03 and breath_events == 0
    has_deep_breaths = deep_breaths > 0

    if has_deep_breaths and overall >= 0.4:
        return "HEAVILY PRODUCED HUMAN", "moderate"
    if has_deep_breaths:
        return "HUMAN", "high"
    if breathiness_paradox and overall >= 0.55:
        return "LIKELY AI", "high"
    if heavily_produced and overall >= 0.55:
        return "AI OR HEAVY PRODUCTION", "low"
    if overall >= 0.7:
        return "LIKELY AI", "high"
    if overall >= 0.55:
        return "POSSIBLY AI", "moderate"
    if overall >= 0.4:
        return "INCONCLUSIVE", "low"
    if overall >= 0.25:
        return "LIKELY HUMAN", "moderate"
    return "HUMAN", "high"


def analyze(stem_dir: Path, upstream: dict[str, object]) -> dict[str, object]:
    """Score self-opposition vs self-agreement from stem signals and upstream vocal analysis."""
    vectors: dict[str, dict[str, object]] = {}
    weights: dict[str, float] = {}

    rel = cast("dict[str, object] | None", upstream.get("vocal_relationships"))
    if rel is not None:
        _score_relationships(rel, vectors, weights)

    reg = cast("dict[str, object] | None", upstream.get("register_tracking"))
    if reg is not None:
        _score_register(reg, vectors, weights)

    breath = cast("dict[str, object] | None", upstream.get("breath_detection"))
    stem = cast("dict[str, object] | None", upstream.get("analyze_stems"))
    if breath is not None and stem is not None:
        _score_breath(breath, stem, vectors, weights)

    if not vectors:
        return cast("dict[str, object]", sanitize(_empty_result()))

    total_weight = sum(weights.values())
    weighted_sum = sum(
        float(cast("float", vectors[k]["score"])) * weights[k] for k in vectors if k in weights
    )
    overall = weighted_sum / total_weight if total_weight > 0 else 0.5
    overall_rounded = round(overall, 3)

    label, confidence = _verdict(overall, vectors)

    result: dict[str, object] = {
        "overall_score": overall_rounded,
        "verdict": label,
        "confidence": confidence,
        "vectors": vectors,
        "weights": {k: round(v, 1) for k, v in weights.items()},
        "vectors_available": len(vectors),
        "vectors_possible": 7,
    }
    return cast("dict[str, object]", sanitize(result))
