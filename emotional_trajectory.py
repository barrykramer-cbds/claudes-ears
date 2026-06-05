#!/usr/bin/env python3
"""Claude's Ears - Emotional Trajectory
Synthesizes temporal channel data into a unified emotional narrative.
Transforms windowed measurements into a story of emotional states."""

import numpy as np, json, sys, os

# Emotional state definitions based on channel combinations
def classify_emotional_state(snap):
    """Classify a temporal window into an emotional state."""
    t = snap.get("tension", 0)
    w = snap.get("warmth", 1.0)
    c = snap.get("consonance", 0.5)
    e = snap.get("rms_p90", -10)
    hp = snap.get("harm_pct", 80)
    od = snap.get("onset_density", 3)

    # Energy level
    if e > -2: energy = "intense"
    elif e > -4: energy = "strong"
    elif e > -7: energy = "moderate"
    elif e > -12: energy = "quiet"
    else: energy = "silent"

    # Emotional quadrant from tension + warmth + consonance
    if t > 0.004 and w > 1.5 and c > 0.56:
        state = "anguished warmth"  # tense but warm - reaching
    elif t > 0.004 and w < 1.2:
        state = "cold tension"  # tense and cool - threat
    elif t > 0.003 and hp < 70:
        state = "aggressive drive"  # tense + percussive
    elif t < 0.001 and c > 0.56 and w > 1.5:
        state = "deep peace"  # low tension, consonant, warm
    elif t < 0.001 and w > 2.0:
        state = "trance / dissolution"  # very low tension, very warm
    elif t < 0.002 and c > 0.55:
        state = "gentle presence"  # moderate calm
    elif t > 0.003:
        state = "rising tension"  # generic tension
    elif w > 1.8 and od < 3:
        state = "floating warmth"  # warm, sparse
    elif hp > 90 and od < 2:
        state = "suspended / ethereal"  # very harmonic, very sparse
    elif od > 5:
        state = "kinetic energy"  # dense onsets, movement
    else:
        state = "neutral flow"  # nothing extreme

    return {"energy": energy, "state": state}

def build_trajectory(temporal_json_path):
    """Build emotional trajectory from temporal segmentation output."""
    print(f"Building emotional trajectory...")

    with open(temporal_json_path) as f:
        data = json.load(f)

    snaps = data.get("snapshots", [])
    narrative = data.get("narrative", {})

    if not snaps:
        return {"error": "No temporal snapshots found"}

    # Classify each window
    trajectory = []
    for snap in snaps:
        emotion = classify_emotional_state(snap)
        trajectory.append({
            "time": snap["time"],
            "t_center": snap["t_center"],
            "energy": emotion["energy"],
            "state": emotion["state"],
            "tension": snap.get("tension", 0),
            "warmth": snap.get("warmth", 0),
            "consonance": snap.get("consonance", 0),
            "rms": snap.get("rms_p90", -20),
        })

    # Detect state transitions (emotional shifts)
    transitions = []
    for i in range(1, len(trajectory)):
        if trajectory[i]["state"] != trajectory[i-1]["state"]:
            transitions.append({
                "time": trajectory[i]["time"],
                "from_state": trajectory[i-1]["state"],
                "to_state": trajectory[i]["state"],
                "from_energy": trajectory[i-1]["energy"],
                "to_energy": trajectory[i]["energy"],
            })

    # Build the narrative arc as a sequence of phases
    # Group consecutive identical states into phases
    phases = []
    if trajectory:
        current = {"state": trajectory[0]["state"], "energy": trajectory[0]["energy"],
                   "start": trajectory[0]["time"], "start_t": trajectory[0]["t_center"],
                   "tensions": [trajectory[0]["tension"]], "warmths": [trajectory[0]["warmth"]]}
        for t in trajectory[1:]:
            if t["state"] == current["state"]:
                current["tensions"].append(t["tension"])
                current["warmths"].append(t["warmth"])
            else:
                current["end"] = t["time"]
                current["end_t"] = t["t_center"]
                current["duration_s"] = round(t["t_center"] - current["start_t"], 1)
                current["tension_trend"] = "rising" if current["tensions"][-1] > current["tensions"][0] * 1.2 else \
                                          "falling" if current["tensions"][-1] < current["tensions"][0] * 0.8 else "steady"
                current["avg_tension"] = round(float(np.mean(current["tensions"])), 5)
                current["avg_warmth"] = round(float(np.mean(current["warmths"])), 3)
                del current["tensions"], current["warmths"], current["start_t"], current["end_t"]
                phases.append(current)
                current = {"state": t["state"], "energy": t["energy"],
                           "start": t["time"], "start_t": t["t_center"],
                           "tensions": [t["tension"]], "warmths": [t["warmth"]]}
        # Final phase
        current["end"] = trajectory[-1]["time"]
        current["duration_s"] = round(trajectory[-1]["t_center"] - current["start_t"], 1)
        current["avg_tension"] = round(float(np.mean(current["tensions"])), 5)
        current["avg_warmth"] = round(float(np.mean(current["warmths"])), 3)
        del current["tensions"], current["warmths"], current["start_t"]
        if "end_t" in current: del current["end_t"]
        phases.append(current)

    # Generate written narrative
    narrative_text = generate_narrative(phases, transitions, narrative)

    results = {
        "total_windows": len(snaps),
        "total_transitions": len(transitions),
        "total_phases": len(phases),
        "unique_states": len(set(t["state"] for t in trajectory)),
        "phases": phases,
        "transitions": transitions[:30],
        "trajectory_summary": [{"time": t["time"], "state": t["state"], "energy": t["energy"]} for t in trajectory],
        "narrative": narrative_text,
    }

    # Print
    print(f"\n{'='*70}")
    print(f"  EMOTIONAL TRAJECTORY")
    print(f"{'='*70}")
    print(f"  {len(phases)} phases, {len(transitions)} transitions, {len(set(t['state'] for t in trajectory))} unique states")

    print(f"\n  JOURNEY:")
    for p in phases:
        dur_bar = "#" * max(1, int(p["duration_s"] / 5))
        print(f"    {p['start']:>5s} - {p['end']:>5s}  {dur_bar:<15s}  [{p['energy']:>8s}]  {p['state']}")

    print(f"\n  KEY TRANSITIONS:")
    for t in transitions[:15]:
        print(f"    {t['time']:>5s}  {t['from_state']} -> {t['to_state']}")

    print(f"\n  NARRATIVE:")
    for line in narrative_text.split(". "):
        print(f"    {line.strip()}.")

    print(f"{'='*70}")
    return results

def generate_narrative(phases, transitions, arc_data):
    """Generate a written narrative of the emotional journey."""
    if not phases:
        return "Insufficient data for narrative."

    parts = []

    # Opening
    p0 = phases[0]
    parts.append(f"Opens in {p0['state']} at {p0['energy']} energy")

    # Middle journey
    prev_state = p0['state']
    for p in phases[1:]:
        if p['state'] != prev_state:
            if p['duration_s'] > 20:
                parts.append(f"shifts to {p['state']} ({p['energy']}) for {p['duration_s']:.0f}s")
            elif p['duration_s'] > 5:
                parts.append(f"passes through {p['state']}")
        prev_state = p['state']

    # Climax
    climax = arc_data.get("climax", {})
    if climax:
        parts.append(f"peaks at {climax.get('time', '?')}")

    # Ending
    pn = phases[-1]
    parts.append(f"resolves to {pn['state']} at {pn['energy']} energy")

    return ". ".join(parts)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python emotional_trajectory.py <temporal_json_file>")
        print("  Input is the output of temporal_segmentation.py")
        sys.exit(1)
    results = build_trajectory(sys.argv[1])
    out = sys.argv[1].replace("_temporal.json", "_emotion.json")
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {out}")
