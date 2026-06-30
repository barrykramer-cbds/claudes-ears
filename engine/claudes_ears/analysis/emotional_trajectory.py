"""Emotional trajectory — per-phase arc from temporal-segmentation snapshots."""

from __future__ import annotations

from typing import cast

import numpy as np

from claudes_ears._sanitize import sanitize


def _to_float(v: object, default: float = 0.0) -> float:
    try:
        return float(cast("float", v))
    except (TypeError, ValueError):
        return default


def _classify_state(snap: dict[str, object]) -> dict[str, str]:
    """Map one snapshot's acoustic dims to an emotional state + energy label."""
    t = _to_float(snap.get("tension"), 0.0)
    w = _to_float(snap.get("warmth"), 1.0)
    c = _to_float(snap.get("consonance"), 0.5)
    e = _to_float(snap.get("rms_p90"), -10.0)
    hp = _to_float(snap.get("harm_pct"), 80.0)
    od = _to_float(snap.get("onset_density"), 3.0)

    if e > -2:
        energy = "intense"
    elif e > -4:
        energy = "strong"
    elif e > -7:
        energy = "moderate"
    elif e > -12:
        energy = "quiet"
    else:
        energy = "silent"

    if t > 0.004 and w > 1.5 and c > 0.56:
        state = "anguished warmth"
    elif t > 0.004 and w < 1.2:
        state = "cold tension"
    elif t > 0.003 and hp < 70:
        state = "aggressive drive"
    elif t < 0.001 and c > 0.56 and w > 1.5:
        state = "deep peace"
    elif t < 0.001 and w > 2.0:
        state = "trance / dissolution"
    elif t < 0.002 and c > 0.55:
        state = "gentle presence"
    elif t > 0.003:
        state = "rising tension"
    elif w > 1.8 and od < 3:
        state = "floating warmth"
    elif hp > 90 and od < 2:
        state = "suspended / ethereal"
    elif od > 5:
        state = "kinetic energy"
    else:
        state = "neutral flow"

    return {"energy": energy, "state": state}


def _empty_result() -> dict[str, object]:
    return {
        "total_windows": 0,
        "total_transitions": 0,
        "total_phases": 0,
        "unique_states": 0,
        "phases": [],
        "transitions": [],
        "trajectory_summary": [],
        "narrative": "",
    }


def _finalize_phase(
    state: str,
    energy: str,
    start: object,
    start_t: float,
    end: object,
    end_t: float,
    tensions: list[float],
    warmths: list[float],
) -> dict[str, object]:
    if len(tensions) >= 2:
        if tensions[-1] > tensions[0] * 1.2:
            trend: str = "rising"
        elif tensions[-1] < tensions[0] * 0.8:
            trend = "falling"
        else:
            trend = "steady"
    else:
        trend = "steady"

    return {
        "state": state,
        "energy": energy,
        "start": start,
        "end": end,
        "duration_s": round(end_t - start_t, 1),
        "tension_trend": trend,
        "avg_tension": round(float(np.mean(tensions)), 5) if tensions else None,
        "avg_warmth": round(float(np.mean(warmths)), 3) if warmths else None,
    }


def _build_phases(trajectory: list[dict[str, object]]) -> list[dict[str, object]]:
    """Merge consecutive equal-state trajectory points into duration-bearing phases."""
    if not trajectory:
        return []

    phases: list[dict[str, object]] = []
    p_state = str(trajectory[0].get("state", ""))
    p_energy = str(trajectory[0].get("energy", ""))
    p_start = trajectory[0].get("time", "")
    p_start_t = _to_float(trajectory[0].get("t_center"), 0.0)
    p_tensions = [_to_float(trajectory[0].get("tension"), 0.0)]
    p_warmths = [_to_float(trajectory[0].get("warmth"), 0.0)]

    for point in trajectory[1:]:
        if point.get("state") == p_state:
            p_tensions.append(_to_float(point.get("tension"), 0.0))
            p_warmths.append(_to_float(point.get("warmth"), 0.0))
        else:
            phases.append(
                _finalize_phase(
                    p_state,
                    p_energy,
                    p_start,
                    p_start_t,
                    point.get("time", ""),
                    _to_float(point.get("t_center"), 0.0),
                    p_tensions,
                    p_warmths,
                )
            )
            p_state = str(point.get("state", ""))
            p_energy = str(point.get("energy", ""))
            p_start = point.get("time", "")
            p_start_t = _to_float(point.get("t_center"), 0.0)
            p_tensions = [_to_float(point.get("tension"), 0.0)]
            p_warmths = [_to_float(point.get("warmth"), 0.0)]

    phases.append(
        _finalize_phase(
            p_state,
            p_energy,
            p_start,
            p_start_t,
            trajectory[-1].get("time", ""),
            _to_float(trajectory[-1].get("t_center"), 0.0),
            p_tensions,
            p_warmths,
        )
    )
    return phases


def _generate_narrative(
    phases: list[dict[str, object]],
    arc: dict[str, object],
) -> str:
    if not phases:
        return ""

    parts: list[str] = []
    p0 = phases[0]
    parts.append(f"Opens in {p0.get('state')} at {p0.get('energy')} energy")

    prev_state = p0.get("state")
    for phase in phases[1:]:
        if phase.get("state") != prev_state:
            dur = _to_float(phase.get("duration_s"), 0.0)
            state = phase.get("state", "")
            energy = phase.get("energy", "")
            if dur > 20:
                parts.append(f"shifts to {state} ({energy}) for {dur:.0f}s")
            elif dur > 5:
                parts.append(f"passes through {state}")
        prev_state = phase.get("state")

    climax = arc.get("climax") if isinstance(arc, dict) else None
    if isinstance(climax, dict):
        parts.append(f"peaks at {climax.get('time', '?')}")

    pn = phases[-1]
    parts.append(f"resolves to {pn.get('state')} at {pn.get('energy')} energy")
    return ". ".join(parts)


def analyze(temporal: dict[str, object]) -> dict[str, object]:
    """Derive emotional phases and transitions from the temporal-segmentation dict."""
    snaps_raw = temporal.get("snapshots")
    snaps: list[dict[str, object]] = (
        [s for s in snaps_raw if isinstance(s, dict)] if isinstance(snaps_raw, list) else []
    )

    if not snaps:
        return cast("dict[str, object]", sanitize(_empty_result()))

    arc_raw = temporal.get("narrative")
    arc: dict[str, object] = arc_raw if isinstance(arc_raw, dict) else {}

    trajectory: list[dict[str, object]] = []
    for snap in snaps:
        emotion = _classify_state(snap)
        trajectory.append(
            {
                "time": snap.get("time", ""),
                "t_center": snap.get("t_center", 0),
                "energy": emotion["energy"],
                "state": emotion["state"],
                "tension": _to_float(snap.get("tension"), 0.0),
                "warmth": _to_float(snap.get("warmth"), 0.0),
                "consonance": _to_float(snap.get("consonance"), 0.0),
                "rms": _to_float(snap.get("rms_p90"), -20.0),
            }
        )

    transitions: list[dict[str, object]] = []
    for i in range(1, len(trajectory)):
        if trajectory[i].get("state") != trajectory[i - 1].get("state"):
            transitions.append(
                {
                    "time": trajectory[i].get("time", ""),
                    "from_state": trajectory[i - 1].get("state", ""),
                    "to_state": trajectory[i].get("state", ""),
                    "from_energy": trajectory[i - 1].get("energy", ""),
                    "to_energy": trajectory[i].get("energy", ""),
                }
            )

    phases = _build_phases(trajectory)
    narrative = _generate_narrative(phases, arc)

    result: dict[str, object] = {
        "total_windows": len(snaps),
        "total_transitions": len(transitions),
        "total_phases": len(phases),
        "unique_states": len({str(t.get("state", "")) for t in trajectory}),
        "phases": phases,
        "transitions": transitions[:30],
        "trajectory_summary": [
            {"time": t.get("time", ""), "state": t.get("state", ""), "energy": t.get("energy", "")}
            for t in trajectory
        ],
        "narrative": narrative,
    }

    return cast("dict[str, object]", sanitize(result))
