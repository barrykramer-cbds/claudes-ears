#!/usr/bin/env python3
"""Claude's Ears - Cross-Track DNA Mapping
Reads all stem analysis results and computes similarity metrics
between tracks. Maps the listener's musical genome as a network."""

import numpy as np, json, sys, os, glob

def load_all_analyses(stems_dir):
    """Load all stem_analysis.json files from the stems directory."""
    tracks = {}
    for d in os.listdir(stems_dir):
        analysis_path = os.path.join(stems_dir, d, "stem_analysis.json")
        if os.path.exists(analysis_path):
            with open(analysis_path) as f:
                data = json.load(f)
            tracks[d] = data
    return tracks

def extract_feature_vector(track_data):
    """Extract a comparable feature vector from stem analysis data."""
    v = track_data.get("vocals", {})
    d = track_data.get("drums", {})
    b = track_data.get("bass", {})
    o = track_data.get("other", {})

    return {
        "vocal_pitch": v.get("pitch_mean_hz", 0),
        "vocal_range": v.get("pitch_range_semitones", 0),
        "vocal_entropy": v.get("vocal_melodic_entropy", 0),
        "vocal_breathiness": v.get("breathiness", 0),
        "vocal_presence": v.get("voiced_fraction", 0),
        "drum_tempo": d.get("tempo_bpm", 0),
        "drum_regularity": d.get("beat_regularity", 0),
        "drum_density": d.get("onsets_per_second", 0),
        "drum_kick_pct": d.get("kit_balance", {}).get("kick", 0),
        "bass_movement": b.get("root_movement_rate", 0),
        "texture_centroid": o.get("centroid_hz", 0),
        "texture_harmonic": o.get("harmonic_pct", 0),
    }

def compute_similarity(vec_a, vec_b):
    """Compute cosine similarity between two feature vectors."""
    keys = set(vec_a.keys()) & set(vec_b.keys())
    a = np.array([vec_a[k] for k in keys])
    b = np.array([vec_b[k] for k in keys])

    # Normalize each dimension
    for i in range(len(a)):
        max_val = max(abs(a[i]), abs(b[i]), 1e-10)
        a[i] /= max_val
        b[i] /= max_val

    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na > 0 and nb > 0:
        return round(float(np.dot(a, b) / (na * nb)), 4)
    return 0

def map_genome(stems_dir):
    """Build cross-track DNA map."""
    print(f"Loading analyses from {stems_dir}...")
    tracks = load_all_analyses(stems_dir)
    print(f"Found {len(tracks)} analyzed tracks")

    if len(tracks) < 2:
        print("Need at least 2 tracks for comparison")
        return {}

    # Extract feature vectors
    vectors = {}
    for name, data in tracks.items():
        vectors[name] = extract_feature_vector(data)

    # Compute pairwise similarity
    names = list(vectors.keys())
    similarity_matrix = {}
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            sim = compute_similarity(vectors[names[i]], vectors[names[j]])
            pair = f"{names[i]} <-> {names[j]}"
            similarity_matrix[pair] = sim

    # Sort by similarity
    sorted_pairs = sorted(similarity_matrix.items(), key=lambda x: -x[1])

    # Find clusters: tracks most similar to each other
    neighbors = {name: [] for name in names}
    for pair, sim in sorted_pairs:
        a, b = pair.split(" <-> ")
        neighbors[a].append({"track": b, "similarity": sim})
        neighbors[b].append({"track": a, "similarity": sim})

    # Sort each track's neighbors by similarity
    for name in neighbors:
        neighbors[name].sort(key=lambda x: -x["similarity"])

    # Collection-wide statistics (the genome)
    all_vectors = list(vectors.values())
    genome = {}
    for key in all_vectors[0].keys():
        vals = [v[key] for v in all_vectors if v[key] > 0]
        if vals:
            genome[key] = {
                "mean": round(float(np.mean(vals)), 3),
                "std": round(float(np.std(vals)), 3),
                "min": round(float(np.min(vals)), 3),
                "max": round(float(np.max(vals)), 3),
                "range_label": f"{np.min(vals):.1f} - {np.max(vals):.1f}"
            }

    # Identify outliers (tracks most different from collection mean)
    mean_vec = {k: genome[k]["mean"] for k in genome}
    distances = {}
    for name, vec in vectors.items():
        dist = 0
        for k in mean_vec:
            if genome[k]["std"] > 0:
                dist += ((vec.get(k, 0) - mean_vec[k]) / genome[k]["std"]) ** 2
        distances[name] = round(float(np.sqrt(dist)), 3)

    most_typical = min(distances, key=distances.get)
    most_unique = max(distances, key=distances.get)

    results = {
        "track_count": len(tracks),
        "genome": genome,
        "most_similar_pairs": [{"pair": p, "similarity": s} for p, s in sorted_pairs[:10]],
        "most_different_pairs": [{"pair": p, "similarity": s} for p, s in sorted_pairs[-5:]],
        "neighbors": {k: v[:3] for k, v in neighbors.items()},
        "most_typical_track": {"name": most_typical, "distance": distances[most_typical]},
        "most_unique_track": {"name": most_unique, "distance": distances[most_unique]},
        "distances_from_center": dict(sorted(distances.items(), key=lambda x: x[1]))
    }

    # Print
    print(f"\n{'='*70}")
    print(f"  MUSICAL GENOME — {len(tracks)} tracks")
    print(f"{'='*70}")

    print(f"\n  COLLECTION DNA:")
    for k, v in genome.items():
        print(f"    {k:>20s}:  {v['range_label']:>20s}  (avg {v['mean']:.2f})")

    print(f"\n  MOST SIMILAR PAIRS:")
    for p in results["most_similar_pairs"][:5]:
        print(f"    {p['similarity']:.3f}  {p['pair']}")

    print(f"\n  MOST DIFFERENT PAIRS:")
    for p in results["most_different_pairs"]:
        print(f"    {p['similarity']:.3f}  {p['pair']}")

    print(f"\n  CENTER OF GRAVITY:")
    print(f"    Most typical: {most_typical}")
    print(f"    Most unique:  {most_unique}")

    print(f"\n  DISTANCE FROM CENTER (lower = more typical):")
    for name, dist in sorted(distances.items(), key=lambda x: x[1]):
        bar = "#" * min(int(dist * 3), 30)
        print(f"    {dist:5.2f}  {bar:<30s}  {name[:50]}")

    print(f"{'='*70}")
    return results

if __name__ == "__main__":
    stems_dir = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLAUDES_EARS_STEMS", os.path.join("stems", "htdemucs"))
    results = map_genome(stems_dir)
    out = os.path.join(stems_dir, "genome_map.json")
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {out}")
