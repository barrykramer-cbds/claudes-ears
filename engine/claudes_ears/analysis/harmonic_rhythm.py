"""Harmonic-rhythm analysis: rate-of-chord-change windows from chord_progression output."""

from __future__ import annotations

from typing import cast

import numpy as np

from claudes_ears._sanitize import sanitize

_RHYTHM_NARRATIVES: dict[str, str] = {
    "turbulent": "harmonic acceleration -- chords churning",
    "active": "harmonic movement -- the progression walks",
    "moderate": "steady harmonic pulse",
    "slow": "harmonic breathing -- chords sustained",
    "stasis": "harmonic stasis -- one chord holding",
}


def _empty_result() -> dict[str, object]:
    return {
        "total_chord_events": 0,
        "total_changes": 0,
        "tempo_bpm": 0.0,
        "duration": 0.0,
        "avg_changes_per_bar": 0.0,
        "max_changes_per_bar": 0.0,
        "min_changes_per_bar": 0.0,
        "harmonic_arc": "too short to classify",
        "total_phases": 0,
        "total_accel_events": 0,
        "phases": [],
        "acceleration_events": [],
        "windows": [],
    }


def _classify_rhythm(changes_per_bar: float) -> tuple[str, str]:
    if changes_per_bar >= 3:
        cls = "turbulent"
    elif changes_per_bar >= 2:
        cls = "active"
    elif changes_per_bar >= 1:
        cls = "moderate"
    elif changes_per_bar >= 0.5:
        cls = "slow"
    else:
        cls = "stasis"
    return cls, _RHYTHM_NARRATIVES[cls]


def _build_windows(
    changes: list[dict[str, object]],
    start_time: float,
    total_duration: float,
    window_beats: int,
    hop_beats: int,
    beat_duration: float,
) -> list[dict[str, object]]:
    window_duration = window_beats * beat_duration
    hop_duration = hop_beats * beat_duration
    windows: list[dict[str, object]] = []
    t = start_time

    while t + window_duration <= total_duration:
        t_end = t + window_duration
        window_changes = sum(
            1
            for c in changes
            if float(cast("float", c["time"])) >= t and float(cast("float", c["time"])) < t_end
        )
        changes_per_beat = window_changes / window_beats
        changes_per_bar = window_changes / (window_beats / 4)
        window_intervals = [
            float(cast("float", changes[i + 1]["time"])) - float(cast("float", changes[i]["time"]))
            for i in range(len(changes) - 1)
            if float(cast("float", changes[i]["time"])) >= t
            and float(cast("float", changes[i]["time"])) < t_end
            and float(cast("float", changes[i + 1]["time"])) < t_end
        ]
        avg_interval = float(np.mean(window_intervals)) if window_intervals else window_duration
        rhythm_class, narrative = _classify_rhythm(changes_per_bar)
        t_label = f"{int(t // 60)}:{int(t % 60):02d}"
        windows.append(
            {
                "time": round(t, 2),
                "label": t_label,
                "changes": window_changes,
                "changes_per_beat": round(changes_per_beat, 3),
                "changes_per_bar": round(changes_per_bar, 2),
                "avg_interval_s": round(avg_interval, 2),
                "rhythm_class": rhythm_class,
                "narrative": narrative,
            }
        )
        t += hop_duration

    return windows


def _build_phases(windows: list[dict[str, object]]) -> list[dict[str, object]]:
    if not windows:
        return []
    phases: list[dict[str, object]] = []
    current_class = str(windows[0]["rhythm_class"])
    current_start_label = str(windows[0]["label"])
    current_start_time = float(cast("float", windows[0]["time"]))
    rates: list[float] = [float(cast("float", windows[0]["changes_per_bar"]))]

    for w in windows[1:]:
        w_class = str(w["rhythm_class"])
        if w_class == current_class:
            rates.append(float(cast("float", w["changes_per_bar"])))
        else:
            phases.append(
                {
                    "class": current_class,
                    "start": current_start_label,
                    "start_time": current_start_time,
                    "end": str(w["label"]),
                    "end_time": float(cast("float", w["time"])),
                    "duration_s": round(float(cast("float", w["time"])) - current_start_time, 1),
                    "avg_changes_per_bar": round(float(np.mean(rates)), 2),
                    "narrative": _RHYTHM_NARRATIVES.get(current_class, ""),
                }
            )
            current_class = w_class
            current_start_label = str(w["label"])
            current_start_time = float(cast("float", w["time"]))
            rates = [float(cast("float", w["changes_per_bar"]))]

    last = windows[-1]
    phases.append(
        {
            "class": current_class,
            "start": current_start_label,
            "start_time": current_start_time,
            "end": str(last["label"]),
            "end_time": float(cast("float", last["time"])),
            "duration_s": round(float(cast("float", last["time"])) - current_start_time, 1),
            "avg_changes_per_bar": round(float(np.mean(rates)), 2),
            "narrative": _RHYTHM_NARRATIVES.get(current_class, ""),
        }
    )
    return phases


def _detect_accel_events(windows: list[dict[str, object]]) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for i in range(1, len(windows)):
        prev_rate = float(cast("float", windows[i - 1]["changes_per_bar"]))
        curr_rate = float(cast("float", windows[i]["changes_per_bar"]))
        delta = curr_rate - prev_rate
        if abs(delta) >= 1.0:
            event_type = "acceleration" if delta > 0 else "deceleration"
            events.append(
                {
                    "time": windows[i]["label"],
                    "type": event_type,
                    "from_rate": round(prev_rate, 2),
                    "to_rate": round(curr_rate, 2),
                    "magnitude": round(delta, 2),
                    "narrative": (
                        f"harmonic rhythm {event_type}s "
                        f"({prev_rate:.1f} -> {curr_rate:.1f} changes/bar)"
                    ),
                }
            )
    return events


def _classify_arc(all_rates: list[float]) -> str:
    if len(all_rates) < 4:
        return "too short to classify"
    quarter = len(all_rates) // 4
    first_q = float(np.mean(all_rates[:quarter]))
    last_q = float(np.mean(all_rates[-quarter:]))
    middle = float(np.mean(all_rates[quarter:-quarter]))
    if last_q > first_q * 1.5:
        return "accelerating (builds toward climax)"
    if first_q > last_q * 1.5:
        return "decelerating (settles from opening)"
    if middle > max(first_q, last_q) * 1.3:
        return "arch (accelerates then settles)"
    if middle < min(first_q, last_q) * 0.7:
        return "valley (settles then accelerates)"
    if float(np.std(all_rates)) < 0.5:
        return "steady (consistent harmonic rhythm)"
    return "variable (no clear overall pattern)"


def analyze(
    chords: dict[str, object],
    window_beats: int = 8,
    hop_beats: int = 4,
) -> dict[str, object]:
    """Derive rate-of-harmonic-change windows from the chord-progression dict.

    ``chords`` is chord_progression's output dict.
    """
    segments = chords.get("segments", [])
    if not isinstance(segments, list) or not segments:
        return cast("dict[str, object]", sanitize(_empty_result()))

    chord_events: list[dict[str, object]] = [
        {
            "time": seg.get("start", 0),
            "chord": seg.get("chord", ""),
        }
        for seg in segments
        if isinstance(seg, dict)
    ]
    if not chord_events:
        return cast("dict[str, object]", sanitize(_empty_result()))

    # Guard against zero/absent tempo — beat_track can return 0.0 on silent input (ISSUE-011).
    raw_tempo = chords.get("tempo", 120)
    try:
        tempo = float(raw_tempo)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        tempo = 120.0
    if tempo <= 0:
        tempo = 120.0
    beat_duration = 60.0 / tempo

    total_duration = float(cast("float", chord_events[-1]["time"]))

    changes: list[dict[str, object]] = []
    prev_chord = str(chord_events[0]["chord"])
    for evt in chord_events[1:]:
        curr_chord = str(evt["chord"])
        if curr_chord != prev_chord:
            t = float(cast("float", evt["time"]))
            changes.append(
                {
                    "time": t,
                    "from": prev_chord,
                    "to": curr_chord,
                    "label": f"{int(t // 60)}:{int(t % 60):02d}",
                }
            )
            prev_chord = curr_chord

    if len(changes) < 2:
        result = _empty_result()
        result["total_chord_events"] = len(chord_events)
        result["total_changes"] = len(changes)
        result["tempo_bpm"] = tempo
        result["duration"] = round(total_duration, 2)
        return cast("dict[str, object]", sanitize(result))

    start_time = float(cast("float", chord_events[0]["time"]))
    windows = _build_windows(
        changes, start_time, total_duration, window_beats, hop_beats, beat_duration
    )
    phases = _build_phases(windows)
    accel_events = _detect_accel_events(windows)
    all_rates = [float(cast("float", w["changes_per_bar"])) for w in windows]
    arc = _classify_arc(all_rates)

    result_full: dict[str, object] = {
        "total_chord_events": len(chord_events),
        "total_changes": len(changes),
        "tempo_bpm": tempo,
        "duration": round(total_duration, 2),
        "avg_changes_per_bar": round(float(np.mean(all_rates)), 2) if all_rates else 0.0,
        "max_changes_per_bar": round(float(np.max(all_rates)), 2) if all_rates else 0.0,
        "min_changes_per_bar": round(float(np.min(all_rates)), 2) if all_rates else 0.0,
        "harmonic_arc": arc,
        "total_phases": len(phases),
        "total_accel_events": len(accel_events),
        "phases": phases,
        "acceleration_events": accel_events[:30],
        "windows": windows,
    }
    return cast("dict[str, object]", sanitize(result_full))
