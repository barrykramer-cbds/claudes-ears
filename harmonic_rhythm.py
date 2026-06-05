#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude's Ears - Harmonic Rhythm
Measures the RATE of harmonic change over time.

A verse sitting on one chord for four bars = harmonic stasis.
A section changing chords every beat = harmonic acceleration.
That acceleration IS the tension building.

The harmonic rhythm is a structural dimension: it tells you
where the arrangement is holding still and where it's moving.
Stasis can mean resolution OR suspended tension (context-dependent).
Acceleration almost always means rising tension or approaching climax.
"""

import numpy as np, json, sys, os

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.bool_, bool)): return bool(obj)
        return super().default(obj)

def analyze_harmonic_rhythm(chords_path, window_beats=8, hop_beats=4):
    """
    Analyze the rate of harmonic change from chord progression data.

    Args:
        chords_path: path to _chords.json from chord_progression.py
        window_beats: number of beats per analysis window (default 8 = 2 bars in 4/4)
        hop_beats: window hop size in beats
    """
    print(f"  Harmonic Rhythm: {os.path.basename(chords_path)}...")

    with open(chords_path, encoding='utf-8') as f:
        data = json.load(f)

    segments = data.get("segments", [])
    if not segments:
        print("    No segment data found.")
        return None

    # Extract chord labels and times from segments
    chord_events = []
    for seg in segments:
        if isinstance(seg, dict):
            chord_events.append({
                "time": seg.get("start", 0),
                "chord": seg.get("chord", ""),
                "confidence": seg.get("avg_confidence", 0),
            })

    if not chord_events:
        print("    No chord events found.")
        return None

    total_duration = chord_events[-1]["time"] if chord_events else 0
    print(f"    {len(chord_events)} chord events over {total_duration:.1f}s")

    # Measure chord changes: where does the chord label change?
    changes = []
    prev_chord = chord_events[0]["chord"]
    for i in range(1, len(chord_events)):
        curr_chord = chord_events[i]["chord"]
        if curr_chord != prev_chord:
            changes.append({
                "time": chord_events[i]["time"],
                "from": prev_chord,
                "to": curr_chord,
                "label": f"{int(chord_events[i]['time']//60)}:{int(chord_events[i]['time']%60):02d}",
            })
            prev_chord = curr_chord

    print(f"    {len(changes)} chord changes detected")

    if len(changes) < 2:
        print("    Too few changes for rhythm analysis.")
        return {"total_changes": len(changes), "harmonic_rhythm_windows": []}

    # Calculate inter-change intervals
    intervals = []
    for i in range(1, len(changes)):
        dt = changes[i]["time"] - changes[i-1]["time"]
        intervals.append(dt)

    # Windowed harmonic rhythm: changes per window
    windows = []
    t = chord_events[0]["time"]

    # Estimate beat duration from tempo
    tempo = data.get("tempo", 120)
    beat_duration = 60.0 / tempo
    window_duration = window_beats * beat_duration
    hop_duration = hop_beats * beat_duration

    while t + window_duration <= total_duration:
        t_end = t + window_duration
        t_label = f"{int(t//60)}:{int(t%60):02d}"

        # Count changes in this window
        window_changes = sum(1 for c in changes if t <= c["time"] < t_end)

        # Changes per beat
        changes_per_beat = window_changes / window_beats

        # Changes per bar (assuming 4/4)
        changes_per_bar = window_changes / (window_beats / 4)

        # Average interval between changes in this window
        window_intervals = [
            changes[i+1]["time"] - changes[i]["time"]
            for i in range(len(changes)-1)
            if t <= changes[i]["time"] < t_end and changes[i+1]["time"] < t_end
        ]
        avg_interval = float(np.mean(window_intervals)) if window_intervals else window_duration

        # Classify rhythm
        if changes_per_bar >= 3:
            rhythm_class = "turbulent"
            narrative = "harmonic acceleration -- chords churning"
        elif changes_per_bar >= 2:
            rhythm_class = "active"
            narrative = "harmonic movement -- the progression is walking"
        elif changes_per_bar >= 1:
            rhythm_class = "moderate"
            narrative = "steady harmonic pulse"
        elif changes_per_bar >= 0.5:
            rhythm_class = "slow"
            narrative = "harmonic breathing -- chords sustained"
        else:
            rhythm_class = "stasis"
            narrative = "harmonic stasis -- one chord holding"

        windows.append({
            "time": round(t, 2),
            "label": t_label,
            "changes": window_changes,
            "changes_per_beat": round(changes_per_beat, 3),
            "changes_per_bar": round(changes_per_bar, 2),
            "avg_interval_s": round(avg_interval, 2),
            "rhythm_class": rhythm_class,
            "narrative": narrative,
        })

        t += hop_duration

    # Build rhythm phases (merge consecutive same-class windows)
    phases = []
    if windows:
        current = {"class": windows[0]["rhythm_class"], "start": windows[0]["label"],
                   "start_time": windows[0]["time"], "changes_list": [windows[0]["changes_per_bar"]]}
        for w in windows[1:]:
            if w["rhythm_class"] == current["class"]:
                current["changes_list"].append(w["changes_per_bar"])
            else:
                current["end"] = w["label"]
                current["end_time"] = w["time"]
                current["duration_s"] = round(w["time"] - current["start_time"], 1)
                current["avg_changes_per_bar"] = round(float(np.mean(current["changes_list"])), 2)
                current["narrative"] = {"turbulent": "harmonic acceleration -- chords churning",
                                       "active": "harmonic movement -- the progression walks",
                                       "moderate": "steady harmonic pulse",
                                       "slow": "harmonic breathing -- chords sustained",
                                       "stasis": "harmonic stasis -- one chord holding"}.get(current["class"], "")
                del current["changes_list"]
                phases.append(current)
                current = {"class": w["rhythm_class"], "start": w["label"],
                           "start_time": w["time"], "changes_list": [w["changes_per_bar"]]}
        # Final phase
        current["end"] = windows[-1]["label"]
        current["end_time"] = windows[-1]["time"]
        current["duration_s"] = round(windows[-1]["time"] - current["start_time"], 1)
        current["avg_changes_per_bar"] = round(float(np.mean(current["changes_list"])), 2)
        current["narrative"] = {"turbulent": "harmonic acceleration -- chords churning",
                               "active": "harmonic movement -- the progression walks",
                               "moderate": "steady harmonic pulse",
                               "slow": "harmonic breathing -- chords sustained",
                               "stasis": "harmonic stasis -- one chord holding"}.get(current["class"], "")
        del current["changes_list"]
        phases.append(current)

    # Detect acceleration/deceleration events
    accel_events = []
    for i in range(1, len(windows)):
        prev_rate = windows[i-1]["changes_per_bar"]
        curr_rate = windows[i]["changes_per_bar"]
        delta = curr_rate - prev_rate
        if abs(delta) >= 1.0:  # significant change
            if delta > 0:
                accel_events.append({
                    "time": windows[i]["label"],
                    "type": "acceleration",
                    "from_rate": round(prev_rate, 2),
                    "to_rate": round(curr_rate, 2),
                    "magnitude": round(delta, 2),
                    "narrative": f"harmonic rhythm accelerates ({prev_rate:.1f} -> {curr_rate:.1f} changes/bar)"
                })
            else:
                accel_events.append({
                    "time": windows[i]["label"],
                    "type": "deceleration",
                    "from_rate": round(prev_rate, 2),
                    "to_rate": round(curr_rate, 2),
                    "magnitude": round(delta, 2),
                    "narrative": f"harmonic rhythm decelerates ({prev_rate:.1f} -> {curr_rate:.1f} changes/bar)"
                })

    # Overall statistics
    all_rates = [w["changes_per_bar"] for w in windows]

    # Classify overall arc
    if len(all_rates) >= 4:
        first_quarter = np.mean(all_rates[:len(all_rates)//4])
        last_quarter = np.mean(all_rates[-len(all_rates)//4:])
        middle = np.mean(all_rates[len(all_rates)//4:-len(all_rates)//4])

        if last_quarter > first_quarter * 1.5:
            arc = "accelerating (builds toward climax)"
        elif first_quarter > last_quarter * 1.5:
            arc = "decelerating (settles from opening)"
        elif middle > max(first_quarter, last_quarter) * 1.3:
            arc = "arch (accelerates then settles)"
        elif middle < min(first_quarter, last_quarter) * 0.7:
            arc = "valley (settles then accelerates)"
        elif np.std(all_rates) < 0.5:
            arc = "steady (consistent harmonic rhythm)"
        else:
            arc = "variable (no clear overall pattern)"
    else:
        arc = "too short to classify"

    results = {
        "total_chord_events": len(chord_events),
        "total_changes": len(changes),
        "tempo_bpm": tempo,
        "duration": round(total_duration, 2),
        "avg_changes_per_bar": round(float(np.mean(all_rates)), 2) if all_rates else 0,
        "max_changes_per_bar": round(float(np.max(all_rates)), 2) if all_rates else 0,
        "min_changes_per_bar": round(float(np.min(all_rates)), 2) if all_rates else 0,
        "harmonic_arc": arc,
        "total_phases": len(phases),
        "total_accel_events": len(accel_events),
        "phases": phases,
        "acceleration_events": accel_events[:30],
        "windows": windows,
    }

    # Print summary
    print(f"\n  HARMONIC RHYTHM")
    print(f"  {'='*60}")
    print(f"  Tempo: {tempo:.0f} BPM | {len(changes)} chord changes in {total_duration:.0f}s")
    print(f"  Average: {results['avg_changes_per_bar']:.2f} changes/bar")
    print(f"  Range: {results['min_changes_per_bar']:.2f} - {results['max_changes_per_bar']:.2f} changes/bar")
    print(f"  Arc: {arc}")
    print(f"  {len(phases)} phases, {len(accel_events)} acceleration events")

    print(f"\n  HARMONIC PHASES:")
    for p in phases:
        bar = "#" * max(1, int(p["avg_changes_per_bar"] * 3))
        print(f"    {p['start']:>5s}-{p['end']:>5s}  {bar:<15s}  {p['class']:<12s}  {p['avg_changes_per_bar']:.1f}/bar")

    if accel_events:
        print(f"\n  ACCELERATION EVENTS:")
        for a in accel_events[:10]:
            arrow = ">>" if a["type"] == "acceleration" else "<<"
            print(f"    {a['time']:>5s}  {arrow}  {a['narrative']}")

    print(f"  {'='*60}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python harmonic_rhythm.py <track_chords.json>")
        print("  Reads chord progression data and measures rate of change.")
        sys.exit(1)

    results = analyze_harmonic_rhythm(sys.argv[1])
    if results:
        out = sys.argv[1].replace('_chords.json', '_harmonic_rhythm.json')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, cls=NpEncoder)
        print(f"\nSaved: {out}")
