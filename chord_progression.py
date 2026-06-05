#!/usr/bin/env python3
"""Claude's Ears - Chord Progression Tracking
Identifies chords per beat and tracks harmonic journey over time."""

import numpy as np, librosa, json, sys, os, warnings
warnings.filterwarnings('ignore')

# Chord templates: major, minor, dim, aug, 7th, m7
TEMPLATES = {}
def build_templates():
    pcs = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    intervals = {
        '': [0,4,7], 'm': [0,3,7], 'dim': [0,3,6], 'aug': [0,4,8],
        '7': [0,4,7,10], 'm7': [0,3,7,10], 'maj7': [0,4,7,11],
        'sus2': [0,2,7], 'sus4': [0,5,7]
    }
    for root_idx, root in enumerate(pcs):
        for suffix, ivs in intervals.items():
            name = f"{root}{suffix}"
            template = np.zeros(12)
            for iv in ivs:
                template[(root_idx + iv) % 12] = 1.0
            template /= np.linalg.norm(template)
            TEMPLATES[name] = template

build_templates()

def identify_chord(chroma_frame):
    """Match a chroma frame to the best chord template."""
    frame = chroma_frame.copy()
    norm = np.linalg.norm(frame)
    if norm < 0.01:
        return "N.C.", 0  # no chord / silence
    frame /= norm

    best_name, best_score = "N.C.", 0
    for name, template in TEMPLATES.items():
        score = float(np.dot(frame, template))
        if score > best_score:
            best_score = score
            best_name = name
    return best_name, round(best_score, 4)

def track_progression(file_path, sr=22050):
    """Extract chord progression aligned to beats."""
    print(f"Loading {os.path.basename(file_path)}...")
    y, sr = librosa.load(file_path, sr=sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    print("  Computing chroma and beats...")
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    tempo_val = float(np.atleast_1d(tempo)[0])

    print(f"  Tempo: {tempo_val:.1f} BPM, {len(beat_times)} beats")

    # Get chord at each beat by averaging chroma between beats
    beat_chords = []
    for i in range(len(beat_frames)):
        start = beat_frames[i]
        end = beat_frames[i+1] if i+1 < len(beat_frames) else chroma.shape[1]
        avg_chroma = chroma[:, start:end].mean(axis=1)
        chord, confidence = identify_chord(avg_chroma)
        beat_chords.append({
            "beat": i+1,
            "time": round(float(beat_times[i]), 3),
            "chord": chord,
            "confidence": confidence
        })

    # Simplify: merge consecutive identical chords into segments
    segments = []
    if beat_chords:
        current = {"chord": beat_chords[0]["chord"], "start": beat_chords[0]["time"],
                   "start_beat": 1, "confidence": [beat_chords[0]["confidence"]]}
        for bc in beat_chords[1:]:
            if bc["chord"] == current["chord"]:
                current["confidence"].append(bc["confidence"])
            else:
                current["end"] = bc["time"]
                current["end_beat"] = bc["beat"] - 1
                current["duration_beats"] = current["end_beat"] - current["start_beat"] + 1
                current["avg_confidence"] = round(float(np.mean(current["confidence"])), 4)
                del current["confidence"]
                segments.append(current)
                current = {"chord": bc["chord"], "start": bc["time"],
                           "start_beat": bc["beat"], "confidence": [bc["confidence"]]}
        # Final segment
        current["end"] = round(duration, 3)
        current["end_beat"] = len(beat_chords)
        current["duration_beats"] = current["end_beat"] - current["start_beat"] + 1
        current["avg_confidence"] = round(float(np.mean(current["confidence"])), 4)
        del current["confidence"]
        segments.append(current)

    # Find the most common progression patterns (4-chord sequences)
    chord_sequence = [s["chord"] for s in segments if s["chord"] != "N.C."]
    patterns = {}
    for i in range(len(chord_sequence) - 3):
        pattern = " -> ".join(chord_sequence[i:i+4])
        patterns[pattern] = patterns.get(pattern, 0) + 1

    top_patterns = sorted(patterns.items(), key=lambda x: -x[1])[:10]

    # Detect modulations (key center shifts)
    window_beats = 8
    key_centers = []
    for i in range(0, len(beat_frames) - window_beats, window_beats // 2):
        window_chroma = chroma[:, beat_frames[i]:beat_frames[min(i+window_beats, len(beat_frames)-1)]].mean(axis=1)
        pcs = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        key_centers.append({
            "time": round(float(beat_times[i]), 2),
            "center": pcs[np.argmax(window_chroma)]
        })

    modulations = []
    for i in range(1, len(key_centers)):
        if key_centers[i]["center"] != key_centers[i-1]["center"]:
            modulations.append({
                "time": key_centers[i]["time"],
                "from": key_centers[i-1]["center"],
                "to": key_centers[i]["center"]
            })

    results = {
        "tempo": round(tempo_val, 1),
        "total_beats": len(beat_chords),
        "total_segments": len(segments),
        "unique_chords": len(set(s["chord"] for s in segments)),
        "segments": segments,
        "top_patterns": [{"pattern": p, "count": c} for p, c in top_patterns],
        "modulations": modulations[:20],
        "chord_sequence_summary": chord_sequence[:50]
    }

    # Print
    print(f"\n{'='*60}")
    print(f"  CHORD PROGRESSION")
    print(f"{'='*60}")
    print(f"  {len(segments)} chord segments, {len(set(s['chord'] for s in segments))} unique chords")
    print(f"\n  PROGRESSION:")
    for s in segments[:30]:
        mins = int(s['start']//60)
        secs = int(s['start']%60)
        bar = "#" * min(s['duration_beats'], 20)
        print(f"    {mins}:{secs:02d}  {s['chord']:>6s}  {bar}  ({s['duration_beats']} beats, conf {s['avg_confidence']:.2f})")
    if len(segments) > 30:
        print(f"    ... ({len(segments)-30} more segments)")

    if top_patterns:
        print(f"\n  RECURRING PATTERNS:")
        for tp in top_patterns[:5]:
            print(f"    {tp[0]}  (x{tp[1]})")

    if modulations:
        print(f"\n  MODULATIONS ({len(modulations)}):")
        for m in modulations[:10]:
            print(f"    {m['time']:.1f}s: {m['from']} -> {m['to']}")

    print(f"{'='*60}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python chord_progression.py <audio_file>")
        sys.exit(1)
    results = track_progression(sys.argv[1])
    out = sys.argv[1].rsplit('.',1)[0] + '_chords.json'
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {out}")
