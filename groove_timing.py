#!/usr/bin/env python3
"""Claude's Ears - Groove Micro-Timing
Where do drum hits land relative to the mathematical grid?
Behind the beat = lazy/heavy. On the beat = mechanical.
Ahead = anxious/urgent. Swing ratio. Push and pull."""

import numpy as np, librosa, json, sys, os, warnings
warnings.filterwarnings('ignore')

def analyze_groove(file_path, sr=22050):
    """Analyze micro-timing characteristics of a drum stem or full mix."""
    print(f"  Groove analysis: {os.path.basename(file_path)}...")
    y, sr = librosa.load(file_path, sr=sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    results = {"duration": round(duration, 2)}

    # Get beat grid (the mathematical "perfect" positions)
    print("    Computing beat grid...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = float(np.atleast_1d(tempo)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    results["tempo"] = round(tempo_val, 1)
    results["beat_count"] = len(beat_times)

    if len(beat_times) < 4:
        results["error"] = "insufficient beats detected"
        return results

    # Get actual onset times (where hits actually land)
    print("    Detecting actual onset positions...")
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=False)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    # For each onset, find the nearest beat and compute the deviation
    print("    Computing micro-timing deviations...")
    deviations_ms = []
    beat_period = 60.0 / tempo_val  # seconds per beat

    for onset in onset_times:
        # Find nearest beat
        dists = np.abs(beat_times - onset)
        nearest_idx = np.argmin(dists)
        nearest_beat = beat_times[nearest_idx]

        # Deviation in milliseconds
        dev_ms = (onset - nearest_beat) * 1000

        # Only count deviations within half a beat (otherwise it's a different beat)
        if abs(dev_ms) < (beat_period * 500):  # half beat in ms
            deviations_ms.append(dev_ms)

    deviations = np.array(deviations_ms)

    if len(deviations) < 10:
        results["error"] = "insufficient onset-beat pairs"
        return results

    # Core metrics
    results["mean_deviation_ms"] = round(float(np.mean(deviations)), 3)
    results["std_deviation_ms"] = round(float(np.std(deviations)), 3)
    results["median_deviation_ms"] = round(float(np.median(deviations)), 3)

    # Feel classification
    mean_dev = results["mean_deviation_ms"]
    if mean_dev > 5:
        results["feel"] = "behind the beat (lazy / heavy / groove)"
    elif mean_dev > 2:
        results["feel"] = "slightly behind (relaxed feel)"
    elif mean_dev < -5:
        results["feel"] = "ahead of the beat (pushing / anxious / urgent)"
    elif mean_dev < -2:
        results["feel"] = "slightly ahead (driving feel)"
    else:
        results["feel"] = "on the grid (mechanical / precise)"

    # Tightness
    std_dev = results["std_deviation_ms"]
    if std_dev < 5:
        results["tightness"] = "machine-tight (quantized or extremely precise)"
    elif std_dev < 10:
        results["tightness"] = "tight (skilled performer)"
    elif std_dev < 20:
        results["tightness"] = "human (natural variation)"
    elif std_dev < 35:
        results["tightness"] = "loose (deliberate or amateur)"
    else:
        results["tightness"] = "very loose (freeform or intentionally sloppy)"

    # Swing detection
    # Swing = alternating long-short pattern in eighth note pairs
    print("    Detecting swing...")
    if len(onset_times) > 20:
        intervals = np.diff(onset_times) * 1000  # ms
        # Look at pairs of consecutive intervals
        swing_ratios = []
        for i in range(0, len(intervals) - 1, 2):
            long_short = max(intervals[i], intervals[i+1]) / (min(intervals[i], intervals[i+1]) + 1e-10)
            if 0.8 < long_short < 3.0:  # reasonable range
                swing_ratios.append(long_short)

        if swing_ratios:
            avg_swing = float(np.mean(swing_ratios))
            results["swing_ratio"] = round(avg_swing, 4)

            if avg_swing > 1.6:
                results["swing_character"] = "heavy swing (jazz / shuffle)"
            elif avg_swing > 1.3:
                results["swing_character"] = "moderate swing (bouncy feel)"
            elif avg_swing > 1.1:
                results["swing_character"] = "slight swing (subtle groove)"
            else:
                results["swing_character"] = "straight (no swing)"

    # Push/pull over time: does the performer drift ahead or behind?
    print("    Analyzing drift...")
    if len(deviations) > 20:
        # Split into quarters and see if deviation changes
        q = len(deviations) // 4
        quarters = [
            float(np.mean(deviations[:q])),
            float(np.mean(deviations[q:2*q])),
            float(np.mean(deviations[2*q:3*q])),
            float(np.mean(deviations[3*q:])),
        ]
        results["drift_quarters_ms"] = [round(q, 2) for q in quarters]

        drift = quarters[-1] - quarters[0]
        if drift > 3:
            results["drift"] = "drifting behind over time (relaxing)"
        elif drift < -3:
            results["drift"] = "drifting ahead over time (building urgency)"
        else:
            results["drift"] = "stable timing (no drift)"

    # Deviation histogram for character
    behind = float(np.sum(deviations > 2)) / len(deviations) * 100
    ahead = float(np.sum(deviations < -2)) / len(deviations) * 100
    on_grid = 100 - behind - ahead

    results["timing_distribution"] = {
        "behind_pct": round(behind, 1),
        "on_grid_pct": round(on_grid, 1),
        "ahead_pct": round(ahead, 1),
    }

    # Print
    print(f"\n  GROOVE MICRO-TIMING")
    print(f"  {'='*50}")
    print(f"  Mean deviation: {results['mean_deviation_ms']:+.1f}ms")
    print(f"  Std deviation:  {results['std_deviation_ms']:.1f}ms")
    print(f"  Feel: {results['feel']}")
    print(f"  Tightness: {results['tightness']}")
    if "swing_character" in results:
        print(f"  Swing: {results['swing_character']} (ratio {results.get('swing_ratio',0):.2f})")
    if "drift" in results:
        print(f"  Drift: {results['drift']}")
    td = results["timing_distribution"]
    print(f"  Distribution: {td['behind_pct']:.0f}% behind | {td['on_grid_pct']:.0f}% on grid | {td['ahead_pct']:.0f}% ahead")
    print(f"  {'='*50}")

    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python groove_timing.py <drum_stem.wav or audio_file>")
        sys.exit(1)
    r = analyze_groove(sys.argv[1])
    out = sys.argv[1].rsplit('.',1)[0] + '_groove.json'
    with open(out, 'w') as f:
        json.dump(r, f, indent=2)
    print(f"\nSaved: {out}")
