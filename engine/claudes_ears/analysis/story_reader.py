"""Grounded story reading — rule-based synthesis from upstream analysis dicts."""

from __future__ import annotations

from typing import cast

from claudes_ears._sanitize import sanitize


def _safe_dict(v: object) -> dict[str, object]:
    return v if isinstance(v, dict) else {}


def _safe_list(v: object) -> list[object]:
    return v if isinstance(v, list) else []


def _safe_str(v: object, default: str = "") -> str:
    return str(v) if v is not None else default


def _to_float(v: object, default: float = 0.0) -> float:
    try:
        return float(cast("float", v))
    except (TypeError, ValueError):
        return default


def _parse_time_s(t: object) -> float:
    """Parse 'M:SS' string or numeric seconds to a float."""
    if isinstance(t, (int, float)):
        return float(t)
    if isinstance(t, str) and ":" in t:
        parts = t.split(":", 1)
        try:
            return int(parts[0]) * 60 + float(parts[1])
        except (ValueError, IndexError):
            pass
    return _to_float(t, 0.0)


def _find_chord_at(t_s: float, segments: list[object]) -> str | None:
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        start = _to_float(seg.get("start"), 0.0)
        end = _to_float(seg.get("end"), 0.0)
        chord = _safe_str(seg.get("chord"))
        if start <= t_s <= end and chord and chord != "N.C.":
            return chord
    return None


def _find_vocal_rel_at(t_s: float, moments: list[object]) -> str | None:
    best: str | None = None
    best_dist = 3.0
    for m in moments:
        if not isinstance(m, dict):
            continue
        dist = abs(_to_float(m.get("time"), 0.0) - t_s)
        if dist < best_dist:
            best_dist = dist
            rel = _safe_str(m.get("relationship"))
            best = rel if rel else None
    return best


def _describe_vessel(
    state: str,
    energy: str,
    vocal_rel: str | None,
    chord: str | None,
) -> str:
    """Describe how the music serves the moment — adapted from the original logic."""
    parts: list[str] = []

    if vocal_rel == "solo":
        parts.append("The arrangement clears the stage — vocal spotlight")
    elif vocal_rel == "support":
        parts.append("The lead voice is held in harmony")
    elif vocal_rel == "dialogue":
        parts.append("Voices in conversation, trading the story")
    elif vocal_rel == "opposition":
        parts.append("Voices collide — no clear lead, collective speech")
    elif vocal_rel == "merge":
        parts.append("All voices converge into one sound")
    elif vocal_rel == "withdraw":
        parts.append("The support steps back, spotlight narrowing")

    if state:
        parts.append(f"The music carries {state}")

    if chord:
        parts.append(f"on {chord}")

    return ". ".join(parts) if parts else ""


def _build_story_moment(
    phase: dict[str, object],
    chord_segments: list[object],
    vr_moments: list[object],
) -> dict[str, object]:
    """Synthesize one story moment from an emotional phase plus available context."""
    state = _safe_str(phase.get("state"))
    energy = _safe_str(phase.get("energy"))
    start_t = _parse_time_s(phase.get("start"))

    chord = _find_chord_at(start_t, chord_segments)
    vocal_rel = _find_vocal_rel_at(start_t, vr_moments)

    return {
        "start": phase.get("start", ""),
        "end": phase.get("end", ""),
        "duration_s": phase.get("duration_s", 0),
        "emotional_state": state,
        "energy": energy,
        "tension_trend": _safe_str(phase.get("tension_trend")),
        "vocal_relationship": vocal_rel,
        "chord": chord,
        "vessel_description": _describe_vessel(state, energy, vocal_rel, chord),
    }


def _build_arc_narrative(
    story_moments: list[dict[str, object]],
    emotional: dict[str, object],
    key: str | None,
    mode: str | None,
) -> str:
    """Build a summary narrative from the story moments and emotional arc."""
    em_narrative = _safe_str(emotional.get("narrative"))
    if not story_moments:
        return em_narrative or ""

    parts: list[str] = []
    if key and mode:
        parts.append(f"In {key} {mode}")

    if em_narrative:
        parts.append(em_narrative)

    vocal_counts: dict[str, int] = {}
    for m in story_moments:
        rel = _safe_str(m.get("vocal_relationship"))
        if rel:
            vocal_counts[rel] = vocal_counts.get(rel, 0) + 1

    if vocal_counts:
        dominant = max(vocal_counts, key=lambda r: vocal_counts[r])
        parts.append(f"predominant vocal texture: {dominant}")

    return ". ".join(parts) if parts else ""


def analyze(deps: dict[str, object]) -> dict[str, object]:
    """Synthesize a musically-grounded story from upstream analysis dicts (rule-based)."""
    vocal_rel = _safe_dict(deps.get("vocal_relationships"))
    emotional = _safe_dict(deps.get("emotional_trajectory"))
    theory = _safe_dict(deps.get("music_theory"))
    chords = _safe_dict(deps.get("chord_progression"))

    key_val = theory.get("key")
    key: str | None = str(key_val) if key_val is not None else None
    mode_val = theory.get("mode")
    mode: str | None = str(mode_val) if mode_val is not None else None
    tempo_val = chords.get("tempo")
    tempo: float | None = _to_float(tempo_val) if tempo_val is not None else None

    chord_segments = _safe_list(chords.get("segments"))
    top_patterns = _safe_list(chords.get("top_patterns"))
    dominant_chord_patterns: list[str] = [
        _safe_str(p.get("pattern"))
        for p in top_patterns[:5]
        if isinstance(p, dict) and p.get("pattern")
    ]

    em_phases = _safe_list(emotional.get("phases"))
    vr_moments = _safe_list(vocal_rel.get("moments"))

    story_moments: list[dict[str, object]] = []
    for phase in em_phases:
        if not isinstance(phase, dict):
            continue
        story_moments.append(_build_story_moment(phase, chord_segments, vr_moments))

    arc_narrative = _build_arc_narrative(story_moments, emotional, key, mode)

    result: dict[str, object] = {
        "total_moments": len(story_moments),
        "key": key,
        "mode": mode,
        "tempo": tempo,
        "dominant_chord_patterns": dominant_chord_patterns,
        "story_moments": story_moments,
        "arc_narrative": arc_narrative,
    }

    return cast("dict[str, object]", sanitize(result))
