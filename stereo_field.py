#!/usr/bin/env python3
"""Claude's Ears - Stereo Field Analysis
Perceives the spatial dimension of music: left/right placement,
width, depth, and how instruments move in the stereo field."""

import numpy as np, librosa, json, sys, os, warnings
warnings.filterwarnings('ignore')

def stereo_analysis(file_path, sr=22050):
    """Analyze the stereo field of an audio file."""
    print(f"Loading stereo: {os.path.basename(file_path)}...")

    # Load as STEREO (the key change!)
    y, sr = librosa.load(file_path, sr=sr, mono=False)

    if y.ndim == 1:
        print("  WARNING: File is mono. No stereo field to analyze.")
        return {"stereo": False, "note": "mono source"}

    duration = y.shape[1] / sr
    left, right = y[0], y[1]
    print(f"  Stereo loaded: {duration:.1f}s, 2 channels")

    results = {"stereo": True, "duration": round(duration, 2)}

    # === MID/SIDE DECOMPOSITION ===
    # Mid = (L+R)/2 (what's in the center)
    # Side = (L-R)/2 (what's on the edges)
    mid = (left + right) / 2
    side = (left - right) / 2

    mid_energy = float(np.sum(mid**2))
    side_energy = float(np.sum(side**2))
    total = mid_energy + side_energy + 1e-10

    results["mid_pct"] = round(mid_energy / total * 100, 1)
    results["side_pct"] = round(side_energy / total * 100, 1)
    results["stereo_width"] = round(side_energy / (mid_energy + 1e-10), 4)

    if results["stereo_width"] > 0.8:
        results["width_desc"] = "very wide - instruments spread across field"
    elif results["stereo_width"] > 0.4:
        results["width_desc"] = "moderately wide - clear L/R separation"
    elif results["stereo_width"] > 0.15:
        results["width_desc"] = "moderate - mostly centered with some spread"
    else:
        results["width_desc"] = "narrow - nearly mono"

    # === LEFT/RIGHT ENERGY BALANCE ===
    left_energy = float(np.sum(left**2))
    right_energy = float(np.sum(right**2))
    balance = (right_energy - left_energy) / (left_energy + right_energy + 1e-10)
    results["lr_balance"] = round(balance, 4)  # -1=all left, +1=all right, 0=centered
    results["balance_desc"] = (
        "left-heavy" if balance < -0.05 else
        "right-heavy" if balance > 0.05 else
        "balanced center"
    )

    # === CORRELATION (how similar L and R are) ===
    # High correlation = mono-like. Low correlation = wide stereo.
    # Negative correlation = out of phase effects
    min_len = min(len(left), len(right))
    correlation = float(np.corrcoef(left[:min_len], right[:min_len])[0, 1])
    results["lr_correlation"] = round(correlation, 4)
    results["correlation_desc"] = (
        "near-mono (L~=R)" if correlation > 0.95 else
        "centered with width" if correlation > 0.8 else
        "wide stereo field" if correlation > 0.5 else
        "very wide / spatial effects" if correlation > 0 else
        "phase effects present"
    )

    # === SPECTRAL WIDTH PER FREQUENCY BAND ===
    # Where in the spectrum does the stereo width live?
    n_fft = 2048
    S_left = np.abs(librosa.stft(left, n_fft=n_fft))
    S_right = np.abs(librosa.stft(right, n_fft=n_fft))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    bands = {
        "sub_bass (20-100)": (20, 100),
        "bass (100-300)": (100, 300),
        "low_mid (300-1000)": (300, 1000),
        "mid (1000-3000)": (1000, 3000),
        "upper_mid (3000-6000)": (3000, 6000),
        "high (6000+)": (6000, sr//2),
    }

    band_width = {}
    for name, (lo, hi) in bands.items():
        mask = (freqs >= lo) & (freqs < hi)
        if mask.any():
            l_band = S_left[mask, :].mean()
            r_band = S_right[mask, :].mean()
            diff = abs(l_band - r_band)
            avg = (l_band + r_band) / 2 + 1e-10
            band_width[name] = round(float(diff / avg), 4)

    results["band_width"] = band_width

    # Where is the stereo width concentrated?
    widest_band = max(band_width, key=band_width.get) if band_width else "unknown"
    narrowest_band = min(band_width, key=band_width.get) if band_width else "unknown"
    results["widest_band"] = widest_band
    results["narrowest_band"] = narrowest_band

    # === TEMPORAL STEREO MOVEMENT ===
    # How does the stereo field change over time?
    hop = 512
    frame_count = min(S_left.shape[1], S_right.shape[1])
    window_frames = int(2 * sr / hop)  # 2-second windows

    width_over_time = []
    for i in range(0, frame_count - window_frames, window_frames // 2):
        l_chunk = S_left[:, i:i+window_frames]
        r_chunk = S_right[:, i:i+window_frames]
        l_e = float(np.sum(l_chunk**2))
        r_e = float(np.sum(r_chunk**2))
        mid_e = float(np.sum(((l_chunk + r_chunk)/2)**2))
        side_e = float(np.sum(((l_chunk - r_chunk)/2)**2))
        width = side_e / (mid_e + 1e-10)
        time_sec = i * hop / sr
        width_over_time.append({
            "time": round(time_sec, 1),
            "width": round(width, 4),
            "balance": round((r_e - l_e) / (l_e + r_e + 1e-10), 4)
        })

    results["width_timeline"] = width_over_time

    # Find moments where stereo field changes dramatically
    if len(width_over_time) > 2:
        widths = [w["width"] for w in width_over_time]
        stereo_events = []
        for i in range(1, len(widths)):
            delta = widths[i] - widths[i-1]
            if abs(delta) > 0.1:
                stereo_events.append({
                    "time": width_over_time[i]["time"],
                    "type": "WIDEN" if delta > 0 else "NARROW",
                    "magnitude": round(abs(delta), 4)
                })
        results["stereo_events"] = stereo_events[:20]

    # === SUMMARY ===
    print(f"\n  STEREO FIELD ANALYSIS")
    print(f"  {'='*50}")
    print(f"  Width:       {results['stereo_width']:.3f} ({results['width_desc']})")
    print(f"  Balance:     {results['lr_balance']:+.4f} ({results['balance_desc']})")
    print(f"  Correlation: {results['lr_correlation']:.4f} ({results['correlation_desc']})")
    print(f"  Mid/Side:    {results['mid_pct']:.1f}% center / {results['side_pct']:.1f}% edges")
    print(f"  Widest band: {results['widest_band']}")
    print(f"  Narrowest:   {results['narrowest_band']}")
    if results.get("stereo_events"):
        print(f"  Stereo events: {len(results['stereo_events'])}")
        for e in results["stereo_events"][:5]:
            arrow = "<->" if e["type"]=="WIDEN" else "><"
            print(f"    {arrow} {e['type']} at {e['time']:.1f}s (d{e['magnitude']:.3f})")
    print(f"  {'='*50}")

    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python stereo_field.py <audio_file>")
        sys.exit(1)
    results = stereo_analysis(sys.argv[1])
    out = sys.argv[1].rsplit('.',1)[0] + '_stereo.json'
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {out}")
