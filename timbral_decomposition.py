#!/usr/bin/env python3
"""Claude's Ears - Timbral Decomposition
Cracks open any stem (especially "other") to find distinct
instrumental voices within it using NMF spectral decomposition.

Instead of one blob called "other," this identifies:
- How many distinct timbral sources exist
- What each one sounds like (spectral signature)
- When each one plays (activation timeline)
- What instrument each likely is (classification)
"""

import numpy as np, librosa, json, sys, os, warnings
warnings.filterwarnings('ignore')
from sklearn.decomposition import NMF

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

# Instrument spectral signatures for classification
# Each is a rough centroid range + spectral shape descriptor
INSTRUMENT_TEMPLATES = {
    "bass guitar / synth bass": {"centroid_range": (60, 300), "harmonic_min": 0.7},
    "electric guitar (clean)": {"centroid_range": (800, 2500), "harmonic_min": 0.6},
    "electric guitar (distorted)": {"centroid_range": (1500, 4000), "harmonic_min": 0.3},
    "acoustic guitar": {"centroid_range": (600, 2000), "harmonic_min": 0.7},
    "piano / keys": {"centroid_range": (400, 3000), "harmonic_min": 0.75},
    "synth pad": {"centroid_range": (300, 2000), "harmonic_min": 0.8},
    "synth lead": {"centroid_range": (1000, 5000), "harmonic_min": 0.6},
    "strings / orchestral": {"centroid_range": (300, 3500), "harmonic_min": 0.85},
    "brass": {"centroid_range": (500, 3000), "harmonic_min": 0.7},
    "woodwind / flute": {"centroid_range": (800, 4000), "harmonic_min": 0.8},
    "sitar / plucked string": {"centroid_range": (200, 5000), "harmonic_min": 0.5},
    "percussion / transient": {"centroid_range": (2000, 8000), "harmonic_min": 0.0},
    "ambient / noise / texture": {"centroid_range": (1000, 8000), "harmonic_min": 0.0},
    "choir / vocal texture": {"centroid_range": (300, 3000), "harmonic_min": 0.7},
}

def classify_component(centroid, harmonic_pct, bandwidth, attack_sharpness):
    """Classify a spectral component by matching to instrument templates."""
    best_match = "unknown"
    best_score = 0

    for name, template in INSTRUMENT_TEMPLATES.items():
        score = 0
        lo, hi = template["centroid_range"]

        # Centroid in range?
        if lo <= centroid <= hi:
            # How centered in the range
            mid = (lo + hi) / 2
            range_width = hi - lo
            score += max(0, 1 - abs(centroid - mid) / range_width) * 3
        else:
            # Penalize but don't eliminate
            dist = min(abs(centroid - lo), abs(centroid - hi))
            score -= dist / 1000

        # Harmonic content match
        if harmonic_pct / 100 >= template["harmonic_min"]:
            score += 2
        else:
            score -= 1

        # Attack sharpness (transient vs sustained)
        if "percussion" in name or "transient" in name:
            if attack_sharpness > 0.5: score += 2
        elif "pad" in name or "strings" in name or "ambient" in name:
            if attack_sharpness < 0.3: score += 2

        if score > best_score:
            best_score = score
            best_match = name

    return best_match, round(best_score, 2)

def decompose_stem(file_path, n_components=4, sr=22050):
    """
    Decompose a stem into N timbral components using NMF.
    Returns spectral profiles and activation timelines for each component.
    """
    print(f"  Timbral decomposition: {os.path.basename(file_path)}")
    print(f"  Seeking {n_components} components...")

    y, sr = librosa.load(file_path, sr=sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    # Compute magnitude spectrogram
    n_fft = 2048
    hop = 512
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    # Run NMF decomposition
    print(f"  Running NMF on {S.shape[0]} freq bins x {S.shape[1]} frames...")
    model = NMF(n_components=n_components, init='nndsvd', max_iter=300, random_state=42)
    W = model.fit_transform(S)  # W: freq_bins x components (spectral templates)
    H = model.components_         # H: components x time_frames (activations)

    reconstruction_error = model.reconstruction_err_
    print(f"  Reconstruction error: {reconstruction_error:.2f}")

    # Analyze each component
    components = []
    for i in range(n_components):
        spectral_template = W[:, i]
        activation = H[i, :]

        # Spectral characteristics of this component
        if spectral_template.sum() > 0:
            weights = spectral_template / spectral_template.sum()
            centroid = float(np.sum(weights * freqs))
        else:
            centroid = 0

        # Bandwidth
        if centroid > 0 and spectral_template.sum() > 0:
            bandwidth = float(np.sqrt(np.sum(weights * (freqs - centroid)**2)))
        else:
            bandwidth = 0

        # Harmonic content estimate
        # Use autocorrelation of the spectral template
        template_norm = spectral_template / (spectral_template.max() + 1e-10)
        peaks = []
        for j in range(1, len(template_norm) - 1):
            if template_norm[j] > 0.2 and template_norm[j] > template_norm[j-1] and template_norm[j] > template_norm[j+1]:
                peaks.append(j)

        # Check if peaks are harmonically related
        if len(peaks) >= 2:
            ratios = [freqs[peaks[k]] / (freqs[peaks[0]] + 1e-10) for k in range(1, min(5, len(peaks)))]
            harmonic_ratios = [r for r in ratios if any(abs(r - n) < 0.15 for n in range(1, 8))]
            harmonic_pct = len(harmonic_ratios) / max(1, len(ratios)) * 100
        else:
            harmonic_pct = 50  # uncertain

        # Attack sharpness (how sudden are the onsets)
        activation_diff = np.diff(activation)
        attack_sharpness = float(np.percentile(np.abs(activation_diff), 95)) / (np.mean(activation) + 1e-10)
        attack_sharpness = min(1.0, attack_sharpness)

        # Activation statistics
        active_frames = np.sum(activation > activation.max() * 0.1)
        active_pct = float(active_frames / len(activation) * 100)

        # Energy contribution
        energy = float(np.sum(activation ** 2))

        # When is this component most active? (temporal regions)
        frame_times = librosa.frames_to_time(np.arange(len(activation)), sr=sr, hop_length=hop)
        peak_time = float(frame_times[np.argmax(activation)])

        # Activation envelope (downsample for storage)
        n_points = min(100, len(activation))
        indices = np.linspace(0, len(activation)-1, n_points, dtype=int)
        envelope = [{"time": round(float(frame_times[idx]), 2),
                     "level": round(float(activation[idx] / (activation.max() + 1e-10)), 4)}
                    for idx in indices]

        # Classify
        instrument, confidence = classify_component(centroid, harmonic_pct, bandwidth, attack_sharpness)

        # Spectral profile (top frequencies)
        top_freq_indices = np.argsort(spectral_template)[-10:][::-1]
        top_freqs = [{"hz": round(float(freqs[idx]), 1),
                      "weight": round(float(spectral_template[idx] / (spectral_template.max() + 1e-10)), 4)}
                     for idx in top_freq_indices if freqs[idx] > 0]

        comp = {
            "component": i + 1,
            "centroid_hz": round(centroid, 1),
            "bandwidth_hz": round(bandwidth, 1),
            "harmonic_pct": round(harmonic_pct, 1),
            "attack_sharpness": round(attack_sharpness, 4),
            "attack_type": "transient" if attack_sharpness > 0.5 else "sustained" if attack_sharpness < 0.2 else "moderate",
            "active_pct": round(active_pct, 1),
            "energy_contribution": round(energy, 2),
            "peak_time": round(peak_time, 2),
            "peak_time_label": f"{int(peak_time//60)}:{int(peak_time%60):02d}",
            "instrument_guess": instrument,
            "classification_confidence": confidence,
            "top_frequencies": top_freqs[:5],
            "activation_envelope": envelope,
        }
        components.append(comp)

    # Sort by energy contribution
    components.sort(key=lambda c: -c["energy_contribution"])

    # Assign rank labels
    for idx, c in enumerate(components):
        total_energy = sum(comp["energy_contribution"] for comp in components)
        c["energy_pct"] = round(c["energy_contribution"] / (total_energy + 1e-10) * 100, 1)
        c["rank"] = idx + 1

    results = {
        "duration": round(duration, 2),
        "n_components": n_components,
        "reconstruction_error": round(reconstruction_error, 2),
        "components": components,
    }

    # Print summary
    print(f"\n  TIMBRAL DECOMPOSITION - {n_components} components found")
    print(f"  {'='*60}")
    for c in components:
        bar = "#" * int(c["energy_pct"] / 2)
        print(f"  #{c['rank']}  {bar:<30s}  {c['energy_pct']:5.1f}%")
        print(f"      Centroid: {c['centroid_hz']:.0f} Hz | BW: {c['bandwidth_hz']:.0f} Hz | Harm: {c['harmonic_pct']:.0f}%")
        print(f"      Attack: {c['attack_type']} ({c['attack_sharpness']:.3f}) | Active: {c['active_pct']:.0f}% | Peak: {c['peak_time_label']}")
        print(f"      -> {c['instrument_guess']} (conf: {c['classification_confidence']})")
    print(f"  {'='*60}")

    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python timbral_decomposition.py <stem.wav> [n_components]")
        print("  Default: 4 components. Try 3-6 depending on mix complexity.")
        sys.exit(1)

    n_comp = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    results = decompose_stem(sys.argv[1], n_components=n_comp)
    out = sys.argv[1].rsplit('.', 1)[0] + '_timbral.json'
    with open(out, 'w') as f:
        json.dump(results, f, indent=2, cls=NpEncoder)
    print(f"\nSaved: {out}")
