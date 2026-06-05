#!/usr/bin/env python3
"""Claude's Ears - Vocal Interval Extraction
Detects pitch relationships between simultaneous vocal lines.
A parallel third is comfort. A parallel second is tension.
A fifth is power. An octave is reinforcement."""

import numpy as np, librosa, json, sys, warnings
warnings.filterwarnings('ignore')

INTERVAL_NAMES = {
    0: ("unison", "unity / reinforcement"),
    1: ("minor 2nd", "tension / dissonance / rub"),
    2: ("major 2nd", "mild tension / passing"),
    3: ("minor 3rd", "dark sweetness / melancholy"),
    4: ("major 3rd", "bright sweetness / joy"),
    5: ("perfect 4th", "openness / suspension"),
    6: ("tritone", "maximum tension / the devil's interval"),
    7: ("perfect 5th", "power / strength / medieval"),
    8: ("minor 6th", "yearning / bittersweet"),
    9: ("major 6th", "warmth / golden ratio interval"),
    10: ("minor 7th", "blues / funk / unresolved"),
    11: ("major 7th", "reaching / almost-octave tension"),
    12: ("octave", "power doubling / fullness"),
}

def extract_intervals(vocal_path, sr=22050):
    """
    Detect simultaneous pitch lines in a vocal stem and
    extract the intervals between them.
    """
    print(f"  Loading vocal stem...")
    y, sr = librosa.load(vocal_path, sr=sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    # Use CQT for better pitch resolution
    print("  Computing CQT for polyphonic pitch detection...")
    C = np.abs(librosa.cqt(y, sr=sr, hop_length=512,
                           fmin=librosa.note_to_hz('C2'),
                           n_bins=60, bins_per_octave=12))

    # Find frames with multiple strong pitch peaks
    print("  Detecting simultaneous pitches...")
    intervals_found = []
    interval_counts = {i: 0 for i in range(13)}

    for frame_idx in range(C.shape[1]):
        frame = C[:, frame_idx]
        if frame.max() < 0.01:
            continue

        # Normalize
        frame_norm = frame / frame.max()

        # Find peaks above threshold
        threshold = 0.3
        peaks = []
        for i in range(1, len(frame_norm)-1):
            if (frame_norm[i] > threshold and
                frame_norm[i] > frame_norm[i-1] and
                frame_norm[i] > frame_norm[i+1]):
                peaks.append(i)

        if len(peaks) >= 2:
            # Compute intervals between all peak pairs
            for i in range(len(peaks)):
                for j in range(i+1, len(peaks)):
                    interval_semitones = abs(peaks[j] - peaks[i])
                    # Reduce to within octave for classification
                    interval_class = interval_semitones % 12
                    if interval_class <= 12:
                        interval_counts[interval_class] += 1

                        # Record with timing (sample every 10th frame to save space)
                        if frame_idx % 10 == 0:
                            time_sec = frame_idx * 512 / sr
                            intervals_found.append({
                                "time": round(time_sec, 2),
                                "interval": interval_class,
                                "semitones_raw": interval_semitones,
                            })

    # Analyze interval distribution
    total_intervals = sum(interval_counts.values())
    interval_profile = []
    for semitones in range(13):
        count = interval_counts[semitones]
        if total_intervals > 0:
            pct = count / total_intervals * 100
        else:
            pct = 0
        name, meaning = INTERVAL_NAMES[semitones]
        interval_profile.append({
            "semitones": semitones,
            "name": name,
            "meaning": meaning,
            "count": count,
            "pct": round(pct, 2)
        })

    # Sort by prevalence
    interval_profile.sort(key=lambda x: -x["count"])

    # Compute harmonic character from interval distribution
    if total_intervals > 0:
        consonant = sum(interval_counts[i] for i in [0, 3, 4, 5, 7, 8, 9, 12])
        dissonant = sum(interval_counts[i] for i in [1, 2, 6, 10, 11])
        consonance_ratio = consonant / total_intervals

        # Sweet vs dark
        sweet = interval_counts[3] + interval_counts[4]  # thirds
        power = interval_counts[7] + interval_counts[0] + interval_counts.get(12, 0)  # fifths + unisons + octaves
        tension = interval_counts[1] + interval_counts[6] + interval_counts[11]  # seconds + tritones + maj7

        if sweet > power and sweet > tension:
            character = "sweet harmonies (thirds dominant)"
        elif power > sweet and power > tension:
            character = "power harmonies (fifths/unisons dominant)"
        elif tension > sweet and tension > power:
            character = "tense harmonies (dissonance dominant)"
        else:
            character = "balanced harmonic palette"
    else:
        consonance_ratio = 0
        character = "insufficient harmonic data"

    results = {
        "duration": round(duration, 2),
        "total_interval_events": total_intervals,
        "consonance_ratio": round(consonance_ratio, 4),
        "harmonic_character": character,
        "interval_profile": interval_profile,
        "sample_intervals": intervals_found[:200],
    }

    # Dominant interval
    if interval_profile:
        dom = interval_profile[0]
        results["dominant_interval"] = {
            "name": dom["name"],
            "meaning": dom["meaning"],
            "pct": dom["pct"]
        }

    # Print
    print(f"\n  VOCAL INTERVAL ANALYSIS")
    print(f"  {'='*50}")
    print(f"  Total interval events: {total_intervals}")
    print(f"  Consonance ratio: {consonance_ratio:.3f}")
    print(f"  Character: {character}")
    print(f"\n  INTERVAL DISTRIBUTION:")
    for ip in interval_profile[:8]:
        if ip["count"] > 0:
            bar = "#" * min(int(ip["pct"]), 40)
            print(f"    {ip['name']:>12s}  {bar:<40s}  {ip['pct']:5.1f}%  ({ip['meaning']})")
    print(f"  {'='*50}")

    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vocal_intervals.py <vocals.wav>")
        sys.exit(1)
    results = extract_intervals(sys.argv[1])
    out = sys.argv[1].rsplit('.',1)[0] + '_intervals.json'
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {out}")
