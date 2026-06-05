#!/usr/bin/env python3
"""Claude's Ears - Vocal Narrative / Lead-Chorus Separation (Module 23)
Separates the lead vocal from backing vocals/chorus within the
vocal stem. Maps the dramatic interplay: who speaks when, who
answers, who dominates, when do they merge.

The story riding the ocean.
"""

import numpy as np, librosa, json, sys, os, warnings
warnings.filterwarnings('ignore')

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

def analyze_vocal_narrative(vocal_path, sr=22050, window_sec=3.0):
    """
    Analyze the lead vs chorus dynamic within a vocal stem.
    Uses spectral width, harmonic peak count, and pitch spread
    to distinguish solo voice from chorus/ensemble sections.
    """
    print(f"  Vocal Narrative: {os.path.basename(vocal_path)}...")
    y, sr = librosa.load(vocal_path, sr=sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    hop = 512
    n_fft = 2048
    window_samples = int(window_sec * sr)
    hop_samples = int(window_sec * sr / 2)  # 50% overlap

    segments = []
    pos = 0

    while pos + window_samples <= len(y):
        seg = y[pos:pos + window_samples]
        t_center = (pos + window_samples / 2) / sr

        # Skip near-silence
        rms = np.sqrt(np.mean(seg**2))
        if rms < 0.005:
            segments.append({
                "time": round(t_center, 2),
                "label": f"{int(t_center//60)}:{int(t_center%60):02d}",
                "type": "silence",
                "energy_db": -60,
                "peak_count": 0,
                "pitch_spread": 0,
                "spectral_width": 0,
                "solo_score": 0,
                "chorus_score": 0,
            })
            pos += hop_samples
            continue

        energy_db = round(float(20 * np.log10(rms + 1e-10)), 2)

        # CQT for polyphonic pitch detection
        C = np.abs(librosa.cqt(seg, sr=sr, hop_length=hop,
                               fmin=librosa.note_to_hz('C2'),
                               n_bins=60, bins_per_octave=12))

        # Count simultaneous peaks per frame
        peak_counts = []
        for frame_idx in range(C.shape[1]):
            frame = C[:, frame_idx]
            if frame.max() < 0.01:
                continue
            frame_norm = frame / frame.max()
            threshold = 0.25
            peaks = 0
            for k in range(1, len(frame_norm)-1):
                if (frame_norm[k] > threshold and
                    frame_norm[k] > frame_norm[k-1] and
                    frame_norm[k] > frame_norm[k+1]):
                    peaks += 1
            peak_counts.append(peaks)

        mean_peaks = float(np.mean(peak_counts)) if peak_counts else 0
        max_peaks = float(np.max(peak_counts)) if peak_counts else 0

        # Pitch spread (variance of detected pitches)
        pitches, magnitudes = librosa.piptrack(y=seg, sr=sr, n_fft=n_fft, hop_length=hop)
        active_pitches = []
        for frame_idx in range(pitches.shape[1]):
            frame_pitches = pitches[:, frame_idx]
            frame_mags = magnitudes[:, frame_idx]
            # Get pitches above threshold
            strong = frame_pitches[frame_mags > np.percentile(frame_mags[frame_mags > 0], 50) if frame_mags.max() > 0 else 0]
            strong = strong[strong > 80]  # above 80 Hz
            if len(strong) > 0:
                active_pitches.extend(strong.tolist())

        if active_pitches:
            pitch_spread = float(np.std(active_pitches))
            pitch_mean = float(np.mean(active_pitches))
        else:
            pitch_spread = 0
            pitch_mean = 0

        # Spectral flatness (chorus = more uniform spectrum)
        flatness = librosa.feature.spectral_flatness(y=seg)[0]
        spectral_width = float(np.mean(flatness))

        # Harmonic density (from harmonic component)
        y_harm = librosa.effects.harmonic(seg)
        harm_energy = float(np.sum(y_harm**2))
        total_energy = float(np.sum(seg**2)) + 1e-10
        harmonic_ratio = harm_energy / total_energy

        # SOLO vs CHORUS scoring
        # Solo: few peaks (1-3), low pitch spread, low spectral flatness
        # Chorus: many peaks (4+), high pitch spread, higher spectral flatness

        solo_indicators = 0
        chorus_indicators = 0

        # Peak count (CALIBRATED v2 - solo voice produces 2-4 peaks naturally)
        if mean_peaks <= 1.5:
            solo_indicators += 4
        elif mean_peaks <= 3.5:
            solo_indicators += 3
        elif mean_peaks <= 5.5:
            solo_indicators += 1
            chorus_indicators += 1
        elif mean_peaks <= 8:
            chorus_indicators += 3
        else:
            chorus_indicators += 4

        # Max peaks (burst density - primary chorus indicator)
        if max_peaks > 8:
            chorus_indicators += 3
        elif max_peaks > 5.5:
            chorus_indicators += 2
        elif max_peaks > 4:
            chorus_indicators += 1
        else:
            solo_indicators += 2

        # Harmonic coherence (mean/max ratio)
        if len(peak_counts) > 0 and mean_peaks > 2 and max_peaks > 0:
            coherence = mean_peaks / max_peaks
            if coherence > 0.7:
                solo_indicators += 2
            elif coherence < 0.4:
                chorus_indicators += 2

        # Spectral flatness (mild)
        if spectral_width < 0.005:
            solo_indicators += 1
        elif spectral_width > 0.05:
            chorus_indicators += 1

        # Harmonic ratio
        if harmonic_ratio > 0.85:
            solo_indicators += 1
        elif harmonic_ratio < 0.6:
            chorus_indicators += 1

        total_score = solo_indicators + chorus_indicators
        if total_score > 0:
            solo_score = solo_indicators / total_score
            chorus_score = chorus_indicators / total_score
        else:
            solo_score = 0.5
            chorus_score = 0.5

        # Classify (calibrated v2)
        if solo_score > 0.58:
            vtype = "solo"
        elif chorus_score > 0.70:
            vtype = "chorus"
        elif chorus_score > 0.50:
            vtype = "lead_with_backing"
        else:
            vtype = "solo"

        segments.append({
            "time": round(t_center, 2),
            "label": f"{int(t_center//60)}:{int(t_center%60):02d}",
            "type": vtype,
            "energy_db": energy_db,
            "peak_count": round(mean_peaks, 1),
            "peak_max": round(max_peaks, 1),
            "pitch_spread": round(pitch_spread, 1),
            "pitch_mean": round(pitch_mean, 1),
            "spectral_width": round(spectral_width, 6),
            "harmonic_ratio": round(harmonic_ratio, 4),
            "solo_score": round(solo_score, 3),
            "chorus_score": round(chorus_score, 3),
        })

        pos += hop_samples

    # Build narrative phases (merge consecutive same-type segments)
    phases = []
    if segments:
        current = {"type": segments[0]["type"], "start": segments[0]["label"],
                   "start_time": segments[0]["time"], "count": 1,
                   "energies": [segments[0]["energy_db"]],
                   "peaks": [segments[0]["peak_count"]]}
        for s in segments[1:]:
            if s["type"] == current["type"]:
                current["count"] += 1
                current["energies"].append(s["energy_db"])
                current["peaks"].append(s["peak_count"])
            else:
                current["end"] = s["label"]
                current["end_time"] = s["time"]
                current["duration_s"] = round(s["time"] - current["start_time"], 1)
                current["avg_energy"] = round(float(np.mean(current["energies"])), 1)
                current["avg_peaks"] = round(float(np.mean(current["peaks"])), 1)
                del current["energies"], current["peaks"], current["count"]
                phases.append(current)
                current = {"type": s["type"], "start": s["label"],
                           "start_time": s["time"], "count": 1,
                           "energies": [s["energy_db"]], "peaks": [s["peak_count"]]}
        # Final phase
        current["end"] = segments[-1]["label"]
        current["end_time"] = segments[-1]["time"]
        current["duration_s"] = round(segments[-1]["time"] - current["start_time"], 1)
        current["avg_energy"] = round(float(np.mean(current["energies"])), 1)
        current["avg_peaks"] = round(float(np.mean(current["peaks"])), 1)
        del current["energies"], current["peaks"], current["count"]
        phases.append(current)

    # Detect call-and-response patterns
    call_response = []
    for i in range(len(phases) - 1):
        a, b = phases[i], phases[i+1]
        if a["type"] == "solo" and b["type"] in ("chorus", "ensemble"):
            call_response.append({
                "call_time": a["start"],
                "call_type": a["type"],
                "response_time": b["start"],
                "response_type": b["type"],
                "pattern": "solo -> chorus (call and response)"
            })
        elif a["type"] in ("chorus", "ensemble") and b["type"] == "solo":
            call_response.append({
                "call_time": a["start"],
                "call_type": a["type"],
                "response_time": b["start"],
                "response_type": b["type"],
                "pattern": "chorus -> solo (return to lead)"
            })

    # Statistics
    type_counts = {}
    type_durations = {}
    for p in phases:
        t = p["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
        type_durations[t] = type_durations.get(t, 0) + p["duration_s"]

    total_dur = sum(type_durations.values())
    type_pcts = {t: round(d / total_dur * 100, 1) for t, d in type_durations.items()} if total_dur > 0 else {}

    results = {
        "duration": round(duration, 2),
        "total_phases": len(phases),
        "total_call_response": len(call_response),
        "type_distribution": type_pcts,
        "phases": phases,
        "call_response_patterns": call_response[:20],
        "segments": segments,
    }

    # Print
    print(f"\n  VOCAL NARRATIVE")
    print(f"  {'='*60}")
    print(f"  {len(phases)} phases, {len(call_response)} call-response patterns")
    print(f"\n  TYPE DISTRIBUTION:")
    for t, pct in sorted(type_pcts.items(), key=lambda x: -x[1]):
        bar = "#" * int(pct / 2)
        print(f"    {t:<20s}  {bar:<30s}  {pct:5.1f}%")

    print(f"\n  NARRATIVE TIMELINE:")
    for p in phases:
        icon = {"solo": "S", "chorus": "CC", "lead_with_backing": "Sc",
                "ensemble": "CCC", "silence": "..."}.get(p["type"], "?")
        dur_bar = "#" * max(1, int(p["duration_s"] / 2))
        print(f"    {p['start']:>5s}-{p['end']:>5s}  {icon:<6s}  {dur_bar:<20s}  {p['type']}")

    if call_response:
        print(f"\n  CALL & RESPONSE:")
        for cr in call_response[:10]:
            print(f"    {cr['call_time']} {cr['pattern']}")

    print(f"  {'='*60}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vocal_narrative.py <vocals.wav> [window_sec]")
        sys.exit(1)
    ws = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    results = analyze_vocal_narrative(sys.argv[1], window_sec=ws)
    out = sys.argv[1].rsplit('.', 1)[0] + '_narrative.json'
    with open(out, 'w') as f:
        json.dump(results, f, indent=2, cls=NpEncoder)
    print(f"\nSaved: {out}")
