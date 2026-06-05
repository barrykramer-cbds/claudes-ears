#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude's Ears - Register Tracking
Detects vocal register transitions: chest voice, head voice,
falsetto, and vocal fry. These are dramatic gear shifts --
the physical mechanism of the voice changes.

A singer reaching falsetto relocates the voice inside the body.
Tracking the register reveals when the performer shifts physical
mechanism to serve the lyric. The register IS the drama.
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

def detect_register(f0, spectral_slope, harmonic_ratio, energy_db, singer_median=300):
    """
    Classify vocal register based on multiple acoustic features.

    Registers:
      CHEST   - full vocal cord vibration, strong lower harmonics,
                warm/full sound.
      HEAD    - partial cord vibration, thinner sound, more upper harmonics.
      FALSETTO- edge vibration only, airy/light, weak lower harmonics.
      FRY     - very low, creaky, sub-phonation.

    We don't use fixed pitch thresholds because register boundaries vary
    per singer. Instead we use relative features:
      - Spectral slope: steep negative = chest, shallow = falsetto
      - Harmonic ratio: high = chest/head, lower = falsetto (more air)
      - F0 relative to track median: high = head/falsetto, low = chest/fry
      - Energy: very low + low pitch = fry
    """
    if f0 <= 0 or energy_db < -50:
        return "silence", 0.0

    # CALIBRATED v2: pitch-relative + spectral slope + harmonic ratio
    # The singer's median pitch determines where chest/head/falsetto
    # boundaries fall for THIS voice. Not absolute thresholds.

    chest_score = 0
    head_score = 0
    falsetto_score = 0
    fry_score = 0

    # Pitch relative to singer's own median (primary discriminator)
    pitch_ratio = f0 / (singer_median + 1e-10)
    if pitch_ratio < 0.7:
        chest_score += 4  # well below median = almost certainly chest
    elif pitch_ratio < 0.9:
        chest_score += 3  # below median = likely chest
        head_score += 1
    elif pitch_ratio < 1.15:
        head_score += 3   # around median = head voice territory
        chest_score += 1
    elif pitch_ratio < 1.5:
        head_score += 2   # above median = upper head or low falsetto
        falsetto_score += 1
    elif pitch_ratio < 2.0:
        falsetto_score += 3  # well above median = likely falsetto
        head_score += 1
    else:
        falsetto_score += 4  # way above median = definitely falsetto

    # Spectral slope (secondary confirmation)
    if spectral_slope < -3.0:
        chest_score += 2
    elif spectral_slope < -1.5:
        chest_score += 1
        head_score += 1
    elif spectral_slope < -0.5:
        head_score += 1
    else:
        falsetto_score += 1  # only +1 now, not +3

    # Harmonic ratio (tertiary)
    if harmonic_ratio > 0.85:
        chest_score += 1
    elif harmonic_ratio < 0.5:
        falsetto_score += 1

    # Fry detection (very low pitch + low energy)
    if f0 < 90 and energy_db < -30:
        fry_score += 4
    elif f0 < 120 and energy_db < -35:
        fry_score += 3

    # Determine winner
    scores = {"chest": chest_score, "head": head_score,
              "falsetto": falsetto_score, "fry": fry_score}
    register = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = scores[register] / total if total > 0 else 0

    return register, round(confidence, 3)

def track_registers(vocal_path, sr=22050, window_sec=0.5):
    """
    Track vocal register across the entire vocal stem.
    Uses short windows (0.5s) to catch rapid transitions.
    """
    print(f"  Register Tracking: {os.path.basename(vocal_path)}...")
    y, sr_actual = librosa.load(vocal_path, sr=sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr_actual)

    hop = 256
    n_fft = 2048
    ws = int(window_sec * sr_actual)
    hs = int(window_sec * sr_actual / 2)  # 50% overlap

    print(f"    Duration: {duration:.1f}s, window: {window_sec}s")

    # Track F0 across entire file for establishing singer's range
    print("    Extracting pitch contour...")
    f0_full, voiced_flag, _ = librosa.pyin(y, fmin=60, fmax=1200, sr=sr_actual, hop_length=hop)
    f0_full = np.nan_to_num(f0_full, nan=0)

    voiced_f0 = f0_full[f0_full > 0]
    if len(voiced_f0) > 0:
        singer_median = float(np.median(voiced_f0))
        singer_low = float(np.percentile(voiced_f0, 10))
        singer_high = float(np.percentile(voiced_f0, 90))
    else:
        singer_median = 300
        singer_low = 150
        singer_high = 500

    print(f"    Singer range: {singer_low:.0f} - {singer_high:.0f} Hz (median {singer_median:.0f} Hz)")

    # Window-by-window register analysis
    print("    Analyzing registers...")
    moments = []
    pos = 0

    while pos + ws <= len(y):
        seg = y[pos:pos + ws]
        t_center = (pos + ws / 2) / sr_actual

        rms = np.sqrt(np.mean(seg**2))
        energy_db = float(20 * np.log10(rms + 1e-10))

        if rms < 0.002:
            moments.append({
                "time": round(t_center, 2),
                "label": f"{int(t_center//60)}:{int(t_center%60):02d}",
                "register": "silence",
                "confidence": 0,
                "f0": 0,
                "energy_db": round(energy_db, 1),
            })
            pos += hs
            continue

        # F0 for this window (sliced from pre-computed full-track pYIN)
        frame_start = pos // hop
        frame_end = min((pos + ws) // hop, len(f0_full))
        seg_f0 = f0_full[frame_start:frame_end]
        voiced_frames = seg_f0[seg_f0 > 0]

        if len(voiced_frames) < 3:
            moments.append({
                "time": round(t_center, 2),
                "label": f"{int(t_center//60)}:{int(t_center%60):02d}",
                "register": "silence",
                "confidence": 0,
                "f0": 0,
                "energy_db": round(energy_db, 1),
            })
            pos += hs
            continue

        mean_f0 = float(np.mean(voiced_frames))

        # Spectral slope (regression on log-magnitude spectrum)
        S = np.abs(librosa.stft(seg, n_fft=n_fft, hop_length=hop))
        mean_spectrum = np.mean(S, axis=1)
        freqs = librosa.fft_frequencies(sr=sr_actual, n_fft=n_fft)

        # Fit slope on log-frequency vs log-magnitude
        valid = (freqs > 80) & (mean_spectrum > 0)
        if np.sum(valid) > 10:
            log_f = np.log10(freqs[valid])
            log_m = np.log10(mean_spectrum[valid] + 1e-10)
            slope = float(np.polyfit(log_f, log_m, 1)[0])
        else:
            slope = -2.0

        # Harmonic ratio
        y_harm = librosa.effects.harmonic(seg)
        harm_energy = float(np.sum(y_harm**2))
        total_energy = float(np.sum(seg**2)) + 1e-10
        harmonic_ratio = harm_energy / total_energy

        # Classify register
        register, confidence = detect_register(mean_f0, slope, harmonic_ratio, energy_db, singer_median=singer_median)

        moments.append({
            "time": round(t_center, 2),
            "label": f"{int(t_center//60)}:{int(t_center%60):02d}",
            "register": register,
            "confidence": round(confidence, 3),
            "f0": round(mean_f0, 1),
            "spectral_slope": round(slope, 3),
            "harmonic_ratio": round(harmonic_ratio, 4),
            "energy_db": round(energy_db, 1),
        })

        pos += hs

    # Build register phases (merge consecutive same-register moments)
    phases = []
    if moments:
        current = {"register": moments[0]["register"], "start": moments[0]["label"],
                   "start_time": moments[0]["time"], "f0s": [moments[0]["f0"]]}
        for m in moments[1:]:
            if m["register"] == current["register"]:
                current["f0s"].append(m["f0"])
            else:
                current["end"] = m["label"]
                current["end_time"] = m["time"]
                current["duration_s"] = round(m["time"] - current["start_time"], 1)
                current["avg_f0"] = round(float(np.mean([f for f in current["f0s"] if f > 0])) if any(f > 0 for f in current["f0s"]) else 0, 1)
                del current["f0s"]
                phases.append(current)
                current = {"register": m["register"], "start": m["label"],
                           "start_time": m["time"], "f0s": [m["f0"]]}
        current["end"] = moments[-1]["label"]
        current["end_time"] = moments[-1]["time"]
        current["duration_s"] = round(moments[-1]["time"] - current["start_time"], 1)
        current["avg_f0"] = round(float(np.mean([f for f in current["f0s"] if f > 0])) if any(f > 0 for f in current["f0s"]) else 0, 1)
        del current["f0s"]
        phases.append(current)

    # Filter short phases (< 1.5s = noise, not real register change)
    filtered_phases = []
    for p in phases:
        if p["register"] == "silence" or p["duration_s"] >= 1.5:
            filtered_phases.append(p)
        elif filtered_phases and filtered_phases[-1]["register"] != "silence":
            # Merge short phase into previous
            filtered_phases[-1]["end"] = p["end"]
            filtered_phases[-1]["end_time"] = p["end_time"]
            filtered_phases[-1]["duration_s"] = round(
                p["end_time"] - filtered_phases[-1]["start_time"], 1)
    phases = filtered_phases

    # Detect transitions (register changes)
    transitions = []
    for i in range(len(phases) - 1):
        a, b = phases[i], phases[i+1]
        if a["register"] != "silence" and b["register"] != "silence":
            # Characterize the transition
            if a["register"] == "chest" and b["register"] in ("head", "falsetto"):
                direction = "ascending"
                drama = "lift"
            elif a["register"] in ("head", "falsetto") and b["register"] == "chest":
                direction = "descending"
                drama = "drop"
            elif a["register"] == "head" and b["register"] == "falsetto":
                direction = "ascending"
                drama = "reach"
            elif a["register"] == "falsetto" and b["register"] == "head":
                direction = "descending"
                drama = "return"
            elif a["register"] == "chest" and b["register"] == "fry":
                direction = "descending"
                drama = "creak"
            else:
                direction = "lateral"
                drama = "shift"

            transitions.append({
                "time": b["start"],
                "from_register": a["register"],
                "to_register": b["register"],
                "from_f0": a["avg_f0"],
                "to_f0": b["avg_f0"],
                "direction": direction,
                "drama": drama,
            })

    # Register distribution
    reg_counts = {}
    reg_durations = {}
    for p in phases:
        r = p["register"]
        if r != "silence":
            reg_counts[r] = reg_counts.get(r, 0) + 1
            reg_durations[r] = reg_durations.get(r, 0) + p["duration_s"]

    total_vocal = sum(reg_durations.values())
    reg_pcts = {r: round(d / total_vocal * 100, 1) for r, d in reg_durations.items()} if total_vocal > 0 else {}

    results = {
        "duration": round(duration, 2),
        "singer_median_f0": singer_median,
        "singer_range_low": singer_low,
        "singer_range_high": singer_high,
        "total_register_phases": len([p for p in phases if p["register"] != "silence"]),
        "total_transitions": len(transitions),
        "register_distribution": reg_pcts,
        "phases": phases,
        "transitions": transitions[:50],
        "moments": moments,
    }

    # Print summary
    print(f"\n  VOCAL REGISTER TRACKING")
    print(f"  {'='*60}")
    print(f"  Singer: {singer_low:.0f} - {singer_high:.0f} Hz (median {singer_median:.0f} Hz)")
    print(f"  {len([p for p in phases if p['register'] != 'silence'])} register phases, {len(transitions)} transitions")

    print(f"\n  REGISTER DISTRIBUTION:")
    icons = {"chest": "LOW", "head": "MID", "falsetto": "HIGH", "fry": "CREAK"}
    for r, pct in sorted(reg_pcts.items(), key=lambda x: -x[1]):
        bar = "#" * int(pct / 2)
        icon = icons.get(r, "?")
        print(f"    [{icon:>5s}] {r:<10s}  {bar:<30s}  {pct:5.1f}%")

    print(f"\n  TRANSITIONS:")
    for t in transitions[:15]:
        arrow = {"lift": ">>", "reach": ">>>", "drop": "<<", "return": "<<<",
                 "creak": "vv", "shift": "<>"}.get(t["drama"], "??")
        print(f"    {t['time']:>5s}  {t['from_register']:>8s} {arrow} {t['to_register']:<8s}  "
              f"({t['from_f0']:.0f} Hz -> {t['to_f0']:.0f} Hz)  [{t['drama']}]")

    if len(transitions) > 15:
        print(f"    ... and {len(transitions) - 15} more transitions")

    print(f"  {'='*60}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python register_tracking.py <vocals.wav> [window_sec]")
        print("  Default window: 0.5s (catches rapid transitions)")
        sys.exit(1)

    ws = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    results = track_registers(sys.argv[1], window_sec=ws)
    out = sys.argv[1].rsplit('.', 1)[0] + '_register.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, cls=NpEncoder)
    print(f"\nSaved: {out}")
