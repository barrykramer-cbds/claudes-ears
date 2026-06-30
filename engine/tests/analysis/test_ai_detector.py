"""ai_detector.analyze: output contract, degraded inputs, single return type."""

from __future__ import annotations

from pathlib import Path

from claudes_ears.analysis import ai_detector

_REQUIRED_KEYS = {
    "overall_score",
    "verdict",
    "confidence",
    "vectors",
    "weights",
    "vectors_available",
    "vectors_possible",
}


def _rel(
    solo: float = 16.0,
    support: float = 30.0,
    opposition: float = 2.5,
    merge: float = 1.3,
) -> dict[str, object]:
    return {
        "relationship_distribution": {
            "solo": solo,
            "support": support,
            "opposition": opposition,
            "merge": merge,
        }
    }


def _reg(
    span_low: float = 100.0,
    span_high: float = 500.0,
    transitions: int = 10,
    duration: float = 120.0,
) -> dict[str, object]:
    return {
        "singer_range_low": span_low,
        "singer_range_high": span_high,
        "total_transitions": transitions,
        "duration": duration,
    }


def _breath(
    total: int = 5,
    bpm: float = 2.5,
    deep: int = 1,
) -> dict[str, object]:
    return {
        "total_breaths": total,
        "breaths_per_minute": bpm,
        "depth_distribution": {"deep": deep},
    }


def _stem(breathiness: float = 0.05) -> dict[str, object]:
    return {"vocals": {"breathiness": breathiness}}


def _vectors(result: dict[str, object]) -> dict[str, object]:
    return result["vectors"]  # type: ignore[return-value]


def test_all_deps_none_returns_degraded_contract() -> None:
    result = ai_detector.analyze(
        stem_dir=Path("/nonexistent"),
        upstream={
            "vocal_relationships": None,
            "register_tracking": None,
            "breath_detection": None,
            "analyze_stems": None,
        },
    )
    assert set(result) >= _REQUIRED_KEYS
    assert result["overall_score"] is None
    assert result["vectors_available"] == 0
    assert "INSUFFICIENT" in str(result["verdict"])
    assert result["confidence"] == "none"


def test_empty_upstream_returns_degraded_contract() -> None:
    result = ai_detector.analyze(stem_dir=Path("/nonexistent"), upstream={})
    assert set(result) >= _REQUIRED_KEYS
    assert result["overall_score"] is None


def test_full_upstream_returns_single_result_dict() -> None:
    """analyze always returns a single dict — never a list, never None."""
    upstream: dict[str, object] = {
        "vocal_relationships": _rel(),
        "register_tracking": _reg(),
        "breath_detection": _breath(),
        "analyze_stems": _stem(),
    }
    result = ai_detector.analyze(stem_dir=Path("/x"), upstream=upstream)
    assert isinstance(result, dict)
    assert set(result) >= _REQUIRED_KEYS
    assert isinstance(result["overall_score"], float)
    assert isinstance(result["verdict"], str)
    assert result["vectors_possible"] == 7


def test_relationships_only_partial_vectors() -> None:
    upstream: dict[str, object] = {
        "vocal_relationships": _rel(),
        "register_tracking": None,
        "breath_detection": None,
        "analyze_stems": None,
    }
    result = ai_detector.analyze(stem_dir=Path("/x"), upstream=upstream)
    assert result["vectors_available"] == 4
    assert "solo_pct" in _vectors(result)
    # < 4 vectors threshold not hit here (4 == 4), but verdict logic handles it
    assert set(result) >= _REQUIRED_KEYS


def test_human_profile_gives_low_score() -> None:
    """High solo, low support, clear opposition, wide range, deep breaths → human."""
    upstream: dict[str, object] = {
        "vocal_relationships": _rel(solo=20.0, support=25.0, opposition=3.0, merge=1.0),
        "register_tracking": _reg(span_low=100.0, span_high=500.0, transitions=15, duration=120.0),
        "breath_detection": _breath(total=12, bpm=4.0, deep=3),
        "analyze_stems": _stem(breathiness=0.1),
    }
    result = ai_detector.analyze(stem_dir=Path("/x"), upstream=upstream)
    assert isinstance(result["overall_score"], float)
    assert result["overall_score"] < 0.55
    assert result["confidence"] in ("moderate", "high")


def test_ai_profile_gives_high_score() -> None:
    """Low solo, high support, no opposition, narrow range, no breaths → AI."""
    upstream: dict[str, object] = {
        "vocal_relationships": _rel(solo=2.0, support=65.0, opposition=0.2, merge=8.0),
        "register_tracking": _reg(span_low=200.0, span_high=310.0, transitions=0, duration=120.0),
        "breath_detection": _breath(total=0, bpm=0.0, deep=0),
        "analyze_stems": _stem(breathiness=0.08),
    }
    result = ai_detector.analyze(stem_dir=Path("/x"), upstream=upstream)
    assert isinstance(result["overall_score"], float)
    assert result["overall_score"] > 0.55


def test_deep_breaths_override_to_human_verdict() -> None:
    """Deep breath events are definitive human physiology — override a mixed score."""
    upstream: dict[str, object] = {
        "vocal_relationships": _rel(solo=2.0, support=60.0, opposition=0.5, merge=6.0),
        "register_tracking": _reg(span_low=200.0, span_high=350.0, transitions=3, duration=120.0),
        "breath_detection": _breath(total=5, bpm=2.5, deep=2),
        "analyze_stems": _stem(breathiness=0.06),
    }
    result = ai_detector.analyze(stem_dir=Path("/x"), upstream=upstream)
    assert "HUMAN" in str(result["verdict"])


def test_breathiness_paradox_flags_ai() -> None:
    """High breathiness + zero breath events = texture without physiology → AI."""
    upstream: dict[str, object] = {
        "vocal_relationships": _rel(solo=3.0, support=62.0, opposition=0.3, merge=7.0),
        "register_tracking": _reg(span_low=200.0, span_high=320.0, transitions=2, duration=120.0),
        "breath_detection": _breath(total=0, bpm=0.0, deep=0),
        "analyze_stems": _stem(breathiness=0.08),
    }
    result = ai_detector.analyze(stem_dir=Path("/x"), upstream=upstream)
    assert result["overall_score"] is not None
    assert "AI" in str(result["verdict"])


def test_register_only_upstream_returns_degraded() -> None:
    """register_tracking alone must not raise; < 4 vectors → INSUFFICIENT verdict."""
    upstream: dict[str, object] = {
        "vocal_relationships": None,
        "register_tracking": _reg(),
        "breath_detection": None,
        "analyze_stems": None,
    }
    result = ai_detector.analyze(stem_dir=Path("/x"), upstream=upstream)
    assert set(result) >= _REQUIRED_KEYS
    assert result["vectors_available"] == 2
    assert "INSUFFICIENT" in str(result["verdict"])


def test_breath_without_stem_skips_vector_7() -> None:
    """breath_detection present but analyze_stems absent — vector 7 must be skipped."""
    upstream: dict[str, object] = {
        "vocal_relationships": _rel(),
        "register_tracking": _reg(),
        "breath_detection": _breath(),
        "analyze_stems": None,
    }
    result = ai_detector.analyze(stem_dir=Path("/x"), upstream=upstream)
    assert "breath_physiology" not in _vectors(result)
    assert result["vectors_available"] == 6
