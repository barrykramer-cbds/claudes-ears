#!/usr/bin/env python3
"""Claude's Ears - Frequency Interaction Map
Computes spectral overlap between stem pairs. Where do instruments
compete for the same space? Where do they complement?"""

import numpy as np, librosa, json, sys, os, warnings
warnings.filterwarnings('ignore')

def compute_interaction(stems_dir, sr=22050):
    """Analyze frequency interactions between all stem pairs."""
    print(f"Loading stems from {stems_dir}...")

    stems = {}
    for name in ["vocals", "drums", "bass", "other"]:
        for ext in [".wav", ".mp3"]:
            p = os.path.join(stems_dir, name + ext)
            if os.path.exists(p):
                y, _ = librosa.load(p, sr=sr, mono=True)
                stems[name] = y
                print(f"  Loaded {name}: {len(y)/sr:.1f}s")
                break

    if len(stems) < 2:
        print("Need at least 2 stems"); return {}

    # Compute spectrograms
    print("  Computing spectrograms...")
    specs = {}
    n_fft = 2048
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    min_len = min(len(y) for y in stems.values())
    for name, y in stems.items():
        specs[name] = np.abs(librosa.stft(y[:min_len], n_fft=n_fft))

    # Define frequency bands
    bands = {
        "sub_bass": (20, 80),
        "bass": (80, 300),
        "low_mid": (300, 800),
        "mid": (800, 2000),
        "upper_mid": (2000, 5000),
        "presence": (5000, 8000),
        "air": (8000, sr//2),
    }

    # Compute overlap for each stem pair in each band
    print("  Computing frequency overlap...")
    pairs = []
    stem_names = list(specs.keys())

    for i in range(len(stem_names)):
        for j in range(i+1, len(stem_names)):
            name_a, name_b = stem_names[i], stem_names[j]
            S_a, S_b = specs[name_a], specs[name_b]

            pair_data = {"pair": f"{name_a} vs {name_b}", "bands": {}}
            total_overlap = 0
            total_energy = 0

            for band_name, (lo, hi) in bands.items():
                mask = (freqs >= lo) & (freqs < hi)
                if not mask.any():
                    continue

                band_a = S_a[mask, :].mean(axis=0)  # energy over time in this band
                band_b = S_b[mask, :].mean(axis=0)

                # Overlap: minimum of the two energies (where they both exist)
                overlap = np.sum(np.minimum(band_a, band_b))
                combined = np.sum(band_a) + np.sum(band_b) + 1e-10
                overlap_ratio = overlap / (combined / 2)  # normalized

                # Correlation: do they move together or independently?
                if np.std(band_a) > 0 and np.std(band_b) > 0:
                    correlation = float(np.corrcoef(band_a, band_b)[0, 1])
                else:
                    correlation = 0

                # Dominance: which stem owns this band?
                e_a = float(np.mean(band_a))
                e_b = float(np.mean(band_b))
                if e_a + e_b > 0:
                    dominance = (e_a - e_b) / (e_a + e_b)
                else:
                    dominance = 0

                pair_data["bands"][band_name] = {
                    "overlap": round(float(overlap_ratio), 4),
                    "correlation": round(correlation, 4),
                    "dominance": round(dominance, 4),  # positive = first stem dominates
                    "dominant": name_a if dominance > 0.1 else name_b if dominance < -0.1 else "shared",
                }

                total_overlap += overlap
                total_energy += combined

            pair_data["overall_overlap"] = round(float(total_overlap / (total_energy / 2 + 1e-10)), 4)

            # Competition assessment
            high_overlap_bands = [b for b, d in pair_data["bands"].items() if d["overlap"] > 0.3]
            if high_overlap_bands:
                pair_data["competition"] = f"competing in: {', '.join(high_overlap_bands)}"
            else:
                pair_data["competition"] = "well separated"

            pairs.append(pair_data)

    # Build territory map: which stem owns which frequency range
    print("  Building frequency territory map...")
    territory = {}
    for band_name, (lo, hi) in bands.items():
        mask = (freqs >= lo) & (freqs < hi)
        if not mask.any():
            continue

        band_energies = {}
        for name, S in specs.items():
            band_energies[name] = float(np.mean(S[mask, :]))

        total = sum(band_energies.values()) + 1e-10
        territory[band_name] = {
            name: round(e / total * 100, 1)
            for name, e in sorted(band_energies.items(), key=lambda x: -x[1])
        }

    results = {
        "stem_count": len(stems),
        "pairs": pairs,
        "territory": territory,
    }

    # Print
    print(f"\n{'='*70}")
    print(f"  FREQUENCY INTERACTION MAP")
    print(f"{'='*70}")

    print(f"\n  TERRITORY (who owns what):")
    for band, owners in territory.items():
        owner_str = " | ".join(f"{n}:{v:.0f}%" for n, v in owners.items())
        print(f"    {band:>12s}:  {owner_str}")

    print(f"\n  PAIR INTERACTIONS:")
    for p in pairs:
        print(f"\n    {p['pair']}  (overall overlap: {p['overall_overlap']:.3f})")
        print(f"    {p['competition']}")
        for band, d in p['bands'].items():
            if d['overlap'] > 0.1:
                bar = "#" * int(d['overlap'] * 30)
                print(f"      {band:>12s}  {bar:<30s}  overlap={d['overlap']:.3f}  dom={d['dominant']}")

    print(f"{'='*70}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python freq_interaction.py <stems_directory>")
        sys.exit(1)
    results = compute_interaction(sys.argv[1])
    out = os.path.join(sys.argv[1], "freq_interaction.json")
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {out}")
