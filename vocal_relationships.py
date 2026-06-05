#!/usr/bin/env python3
"""Claude's Ears - Vocal Relationship Analysis
Hears the STORY between voices: when does support enter,
when does it withdraw, when do voices oppose or merge.

Not "solo vs chorus" but "how do the voices relate to each
other at this moment and what does that relationship mean?"

Five relationship types:
  SOLO      - one voice, alone, carrying the narrative
  SUPPORT   - backing voices enter BELOW the lead, lifting it
  DIALOGUE  - voices in different registers trading phrases
  OPPOSITION- voices singing against each other (call vs refusal)
  MERGE     - voices converging to unison, becoming one
  WITHDRAW  - support thinning, leaving the lead exposed
"""

import numpy as np, librosa, json, sys, os, warnings
warnings.filterwarnings('ignore')

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.bool_, bool)): return bool(obj)
        return super().default(obj)

def analyze_relationships(vocal_path, sr=22050, window_sec=2.0):
    """Track vocal relationships over time."""
    print(f"  Vocal Relationships: {os.path.basename(vocal_path)}...")
    y, sr = librosa.load(vocal_path, sr=sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    hop = 512
    ws = int(window_sec * sr)
    hs = int(window_sec * sr / 2)

    # First pass: establish the lead voice baseline
    # The lead is the most common pitch center across the track
    print("    Establishing lead voice baseline...")
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr, n_fft=2048, hop_length=hop)

    # Find dominant pitch per frame
    dominant_pitches = []
    for frame in range(pitches.shape[1]):
        idx = magnitudes[:, frame].argmax()
        p = pitches[idx, frame]
        if p > 80:
            dominant_pitches.append(p)

    if dominant_pitches:
        lead_pitch_center = float(np.median(dominant_pitches))
        lead_pitch_low = float(np.percentile(dominant_pitches, 25))
        lead_pitch_high = float(np.percentile(dominant_pitches, 75))
    else:
        lead_pitch_center = 300
        lead_pitch_low = 200
        lead_pitch_high = 400

    print(f"    Lead voice center: {lead_pitch_center:.0f} Hz (range {lead_pitch_low:.0f}-{lead_pitch_high:.0f})")

    # Second pass: window-by-window relationship analysis
    print("    Analyzing vocal relationships...")
    moments = []
    prev_density = 0
    prev_relationship = "silence"

    pos = 0
    while pos + ws <= len(y):
        seg = y[pos:pos + ws]
        t_center = (pos + ws / 2) / sr

        rms = np.sqrt(np.mean(seg**2))
        if rms < 0.003:
            moments.append({
                "time": round(t_center, 2),
                "label": f"{int(t_center//60)}:{int(t_center%60):02d}",
                "relationship": "silence",
                "energy_db": -60,
                "density": 0,
                "density_change": 0,
                "lead_present": False,
                "support_register": "none",
                "narrative": "silence"
            })
            prev_density = 0
            prev_relationship = "silence"
            pos += hs
            continue

        energy_db = round(float(20 * np.log10(rms + 1e-10)), 2)

        # Get pitches in this window
        seg_pitches, seg_mags = librosa.piptrack(y=seg, sr=sr, n_fft=2048, hop_length=hop)

        # Collect all strong pitches
        active_pitches = []
        lead_region_energy = 0
        other_region_energy = 0
        below_lead_energy = 0
        above_lead_energy = 0

        for frame in range(seg_pitches.shape[1]):
            frame_p = seg_pitches[:, frame]
            frame_m = seg_mags[:, frame]

            threshold = np.percentile(frame_m[frame_m > 0], 30) if frame_m.max() > 0 else 0

            for idx in range(len(frame_p)):
                if frame_p[idx] > 80 and frame_m[idx] > threshold:
                    active_pitches.append(frame_p[idx])

                    # Categorize by register relative to lead
                    if lead_pitch_low * 0.8 <= frame_p[idx] <= lead_pitch_high * 1.2:
                        lead_region_energy += frame_m[idx]
                    elif frame_p[idx] < lead_pitch_low * 0.8:
                        below_lead_energy += frame_m[idx]
                    else:
                        above_lead_energy += frame_m[idx]

        if not active_pitches:
            moments.append({
                "time": round(t_center, 2),
                "label": f"{int(t_center//60)}:{int(t_center%60):02d}",
                "relationship": "silence",
                "energy_db": energy_db,
                "density": 0,
                "density_change": 0,
                "lead_present": False,
                "support_register": "none",
                "narrative": "instrumental"
            })
            prev_density = 0
            prev_relationship = "silence"
            pos += hs
            continue

        # Density = number of distinct pitch clusters
        from scipy.ndimage import label as scipy_label
        pitch_hist, bin_edges = np.histogram(active_pitches, bins=48, range=(80, 1200))
        smoothed = np.convolve(pitch_hist, np.ones(3)/3, mode='same')
        binary = (smoothed > np.max(smoothed) * 0.15).astype(int)
        labeled, num_clusters = scipy_label(binary)
        density = num_clusters

        density_change = density - prev_density

        # Is the lead voice present?
        total_energy = lead_region_energy + below_lead_energy + above_lead_energy + 1e-10
        lead_pct = lead_region_energy / total_energy
        below_pct = below_lead_energy / total_energy
        above_pct = above_lead_energy / total_energy
        lead_present = lead_pct > 0.2

        # Determine support register
        if below_pct > 0.15 and above_pct > 0.15:
            support_register = "both"
        elif below_pct > 0.15:
            support_register = "below"
        elif above_pct > 0.15:
            support_register = "above"
        else:
            support_register = "none"

        # Determine relationship
        if density <= 1 and lead_present:
            if prev_relationship in ("support", "merge", "dialogue", "opposition") and density_change < 0:
                relationship = "withdraw"
                narrative = "the arrangement opens a spotlight for the lead voice"
            else:
                relationship = "solo"
                narrative = "vocal spotlight  -- one voice expressing the lyric unaccompanied"

        elif density >= 3 and lead_present:
            if support_register == "below":
                relationship = "support"
                narrative = "voices lifting from below, the ground holding the sky"
            elif support_register == "above":
                relationship = "support"
                narrative = "voices shimmering above, adding light"
            elif support_register == "both":
                relationship = "merge"
                narrative = "voices surrounding, becoming one sound"
            else:
                relationship = "support"
                narrative = "voices gathering to carry the lead higher"

        elif density == 2 and lead_present:
            if density_change > 0:
                if support_register == "below":
                    relationship = "support"
                    narrative = "a second voice enters below, offering foundation"
                elif support_register == "above":
                    relationship = "dialogue"
                    narrative = "a voice answers from above"
                else:
                    relationship = "dialogue"
                    narrative = "two voices in conversation"
            elif density_change < 0:
                relationship = "withdraw"
                narrative = "voices stepping back, spotlight narrowing to the lead"
            else:
                if support_register in ("below", "both"):
                    relationship = "support"
                    narrative = "held in harmony, the lead supported"
                else:
                    relationship = "dialogue"
                    narrative = "voices trading space"

        elif not lead_present and density >= 2:
            relationship = "opposition"
            narrative = "voices without a clear lead, collective speech"

        elif density_change < -1:
            relationship = "withdraw"
            narrative = "the arrangement clears the stage for the solo voice"

        else:
            relationship = "solo"
            narrative = "vocal spotlight  -- the performer given the stage to express"

        moments.append({
            "time": round(t_center, 2),
            "label": f"{int(t_center//60)}:{int(t_center%60):02d}",
            "relationship": relationship,
            "energy_db": energy_db,
            "density": density,
            "density_change": density_change,
            "lead_present": lead_present,
            "lead_pct": round(float(lead_pct * 100), 1),
            "below_pct": round(float(below_pct * 100), 1),
            "above_pct": round(float(above_pct * 100), 1),
            "support_register": support_register,
            "narrative": narrative,
        })

        prev_density = density
        prev_relationship = relationship
        pos += hs

    # Build story arc: merge consecutive same-relationship moments
    story = []
    if moments:
        current = {"relationship": moments[0]["relationship"],
                   "narrative": moments[0]["narrative"],
                   "start": moments[0]["label"],
                   "start_time": moments[0]["time"],
                   "moments": [moments[0]]}
        for m in moments[1:]:
            if m["relationship"] == current["relationship"]:
                current["moments"].append(m)
            else:
                current["end"] = m["label"]
                current["duration_s"] = round(m["time"] - current["start_time"], 1)
                current["avg_density"] = round(float(np.mean([x["density"] for x in current["moments"]])), 1)
                del current["moments"]
                story.append(current)
                current = {"relationship": m["relationship"],
                           "narrative": m["narrative"],
                           "start": m["label"],
                           "start_time": m["time"],
                           "moments": [m]}
        current["end"] = moments[-1]["label"]
        current["duration_s"] = round(moments[-1]["time"] - current["start_time"], 1)
        current["avg_density"] = round(float(np.mean([x["density"] for x in current["moments"]])), 1)
        del current["moments"]
        story.append(current)

    # Relationship distribution
    rel_counts = {}
    for m in moments:
        r = m["relationship"]
        rel_counts[r] = rel_counts.get(r, 0) + 1
    total = len(moments)
    rel_pcts = {r: round(c / total * 100, 1) for r, c in rel_counts.items()} if total > 0 else {}

    # Story transitions (relationship changes)
    transitions = []
    for i in range(len(story) - 1):
        transitions.append({
            "time": story[i+1]["start"],
            "from": story[i]["relationship"],
            "to": story[i+1]["relationship"],
            "from_narrative": story[i]["narrative"],
            "to_narrative": story[i+1]["narrative"],
        })

    results = {
        "duration": round(duration, 2),
        "lead_pitch_center": round(lead_pitch_center, 1),
        "total_story_phases": len(story),
        "total_transitions": len(transitions),
        "relationship_distribution": rel_pcts,
        "story": story,
        "transitions": transitions[:30],
        "moments": moments,
    }

    # Print
    print(f"\n  VOCAL RELATIONSHIPS  -- The Story Between Voices")
    print(f"  {'='*60}")
    print(f"  Lead voice: {lead_pitch_center:.0f} Hz")
    print(f"  {len(story)} story phases, {len(transitions)} transitions")

    print(f"\n  DISTRIBUTION:")
    for r, pct in sorted(rel_pcts.items(), key=lambda x: -x[1]):
        bar = "#" * int(pct / 2)
        print(f"    {r:<14s}  {bar:<30s}  {pct:5.1f}%")

    print(f"\n  STORY:")
    for s in story:
        dur_bar = "#" * max(1, int(s["duration_s"] / 2))
        print(f"    {s['start']:>5s}-{s['end']:>5s}  {dur_bar:<15s}  {s['narrative']}")

    print(f"  {'='*60}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vocal_relationships.py <vocals.wav> [window_sec]")
        sys.exit(1)
    ws = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    results = analyze_relationships(sys.argv[1], window_sec=ws)
    out = sys.argv[1].rsplit('.', 1)[0] + '_relationships.json'
    with open(out, 'w') as f:
        json.dump(results, f, indent=2, cls=NpEncoder)
    print(f"\nSaved: {out}")
