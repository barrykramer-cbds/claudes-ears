#!/usr/bin/env python3
"""Claude's Ears - Track Metadata & Temporal Genome
Maps release years and metadata to tracks, enabling
temporal analysis of how music evolved across decades.

The METADATA dict below is an example library used during
development. Replace or extend it with your own tracks.
"""

import json, sys, os

# Track metadata: release year, artist, genre, era (example library)
METADATA = {
    "amy winehouse - rehab": {"year": 2006, "artist": "Amy Winehouse", "genre": "soul/R&B", "era": "2000s"},
    "Bad Religion - Sorrow": {"year": 2002, "artist": "Bad Religion", "genre": "punk rock", "era": "2000s"},
    "Between the Weights": {"year": 2024, "artist": "AI-generated", "genre": "AI-generated", "era": "2020s"},
    "Carl Orff - O Fortuna ~ Carmina Burana": {"year": 1936, "artist": "Carl Orff", "genre": "orchestral cantata", "era": "pre-1950"},
    "Clair de Lune": {"year": 1905, "artist": "Claude Debussy", "genre": "impressionist orchestral", "era": "pre-1950"},
    "Depeche Mode - Fly on the Windscreen - Final Music Video": {"year": 1985, "artist": "Depeche Mode", "genre": "synth-pop/darkwave", "era": "1980s"},
    "Eminem - Rap God (Explicit)": {"year": 2013, "artist": "Eminem", "genre": "hip-hop", "era": "2010s"},
    "Evanescence - Bring Me To Life": {"year": 2003, "artist": "Evanescence", "genre": "gothic rock", "era": "2000s"},
    "Evanescense - Call Me When You're Sober": {"year": 2006, "artist": "Evanescence", "genre": "gothic rock", "era": "2000s"},
    "FAUN - Walpurgisnacht (Official Video)": {"year": 2013, "artist": "FAUN", "genre": "pagan folk", "era": "2010s"},
    "Imagine Dragons - Demons (trimmed)": {"year": 2012, "artist": "Imagine Dragons", "genre": "pop rock", "era": "2010s"},
    "Katy Perry - Dark Horse ft. Juicy J": {"year": 2013, "artist": "Katy Perry", "genre": "pop", "era": "2010s"},
    "Moby - Porcelein": {"year": 1999, "artist": "Moby", "genre": "electronica", "era": "1990s"},
    "Queen - Bohemian Rhapsody": {"year": 1975, "artist": "Queen", "genre": "rock opera", "era": "1970s"},
    "rammstein - du riechst so gut": {"year": 1995, "artist": "Rammstein", "genre": "industrial metal", "era": "1990s"},
    "Ravi Shankar - Raga Mishra Piloo": {"year": 1958, "artist": "Ravi Shankar", "genre": "Indian classical", "era": "1950s"},
    "Siouxie and the Banshees - Kiss Them For Me": {"year": 1991, "artist": "Siouxsie and the Banshees", "genre": "post-punk/new wave", "era": "1990s"},
    "t.A.T.u. - All The Things She Said (Official Music Video)": {"year": 2002, "artist": "t.A.T.u.", "genre": "pop/electronic", "era": "2000s"},
    "The Cure - Disintegration": {"year": 1989, "artist": "The Cure", "genre": "gothic rock/shoegaze", "era": "1980s"},
    "Trip Like I Do": {"year": 1997, "artist": "The Crystal Method", "genre": "big beat/electronica", "era": "1990s"},
    "VALHALLA CALLING by Miracle Of Sound ft. Peyton Parrish - OFFICIAL VIDEO": {"year": 2020, "artist": "Miracle of Sound", "genre": "dark folk", "era": "2020s"},
}

def build_temporal_genome(stems_dir):
    """Build genome map with temporal metadata."""
    # Load existing genome
    genome_path = os.path.join(stems_dir, "genome_map.json")
    if not os.path.exists(genome_path):
        print("Error: genome_map.json not found. Run genome_map.py first.")
        return

    with open(genome_path) as f:
        genome = json.load(f)

    distances = genome.get("distances_from_center", {})

    # Merge metadata with genome data
    tracks = []
    for name, dist in distances.items():
        meta = METADATA.get(name, {"year": 0, "artist": "Unknown", "genre": "unknown", "era": "unknown"})
        tracks.append({
            "name": name,
            "distance": dist,
            "year": meta["year"],
            "artist": meta["artist"],
            "genre": meta["genre"],
            "era": meta["era"],
        })

    # Sort by year
    tracks.sort(key=lambda t: t["year"])

    # Compute temporal patterns
    print(f"\n{'='*80}")
    print(f"  TEMPORAL GENOME — Music Across Time")
    print(f"{'='*80}")

    print(f"\n  TIMELINE (sorted by release year):")
    print(f"  {'YEAR':>6s}  {'DIST':>5s}  {'ERA':<10s}  {'GENRE':<25s}  {'TRACK':<40s}")
    print(f"  {'-'*90}")

    for t in tracks:
        yr = str(t['year']) if t['year'] > 0 else "????"
        bar = "#" * int(t['distance'] * 2)
        print(f"  {yr:>6s}  {t['distance']:5.2f}  {t['era']:<10s}  {t['genre']:<25s}  {t['name'][:40]}")

    # Group by era
    eras = {}
    for t in tracks:
        era = t["era"]
        if era not in eras:
            eras[era] = []
        eras[era].append(t)

    print(f"\n  ERA ANALYSIS:")
    for era in sorted(eras.keys()):
        era_tracks = eras[era]
        avg_dist = sum(t["distance"] for t in era_tracks) / len(era_tracks)
        genres = set(t["genre"] for t in era_tracks)
        print(f"\n  {era} ({len(era_tracks)} tracks, avg distance: {avg_dist:.2f}):")
        for t in era_tracks:
            print(f"    {t['year']}  {t['distance']:5.2f}  {t['artist']}")

    # Temporal correlation: does distance from center correlate with age?
    years = [t["year"] for t in tracks if t["year"] > 0]
    dists = [t["distance"] for t in tracks if t["year"] > 0]

    if len(years) > 3:
        import numpy as np
        corr = np.corrcoef(years, dists)[0, 1]
        print(f"\n  TEMPORAL CORRELATION:")
        print(f"    Year vs Distance from center: {corr:+.4f}")
        if corr > 0.3:
            print(f"    -> Newer tracks tend to be MORE distant from center")
        elif corr < -0.3:
            print(f"    -> Newer tracks tend to be CLOSER to center")
        else:
            print(f"    -> No strong temporal trend — acoustic DNA is era-independent")

    # Find acoustic twins across eras
    print(f"\n  CROSS-ERA ACOUSTIC TWINS:")
    pairs = genome.get("most_similar_pairs", [])
    for p in pairs[:10]:
        pair_str = p["pair"]
        parts = pair_str.split(" <-> ")
        if len(parts) == 2:
            a_meta = METADATA.get(parts[0], {})
            b_meta = METADATA.get(parts[1], {})
            a_era = a_meta.get("era", "?")
            b_era = b_meta.get("era", "?")
            a_year = a_meta.get("year", 0)
            b_year = b_meta.get("year", 0)
            if a_era != b_era and a_year > 0 and b_year > 0:
                gap = abs(a_year - b_year)
                print(f"    {p['similarity']:.3f}  {parts[0][:30]} ({a_year}) <-> {parts[1][:30]} ({b_year})  [{gap} years apart]")

    # Evolution map: how did genres change acoustically?
    print(f"\n  GENRE CLUSTERS:")
    genres = {}
    for t in tracks:
        g = t["genre"]
        if g not in genres:
            genres[g] = []
        genres[g].append(t)

    for genre, gtracks in sorted(genres.items()):
        if len(gtracks) > 1:
            avg_d = sum(t["distance"] for t in gtracks) / len(gtracks)
            years_str = ", ".join(str(t["year"]) for t in gtracks)
            print(f"    {genre}: {len(gtracks)} tracks ({years_str}), avg dist {avg_d:.2f}")

    # Save enhanced genome
    enhanced = {
        "tracks": tracks,
        "eras": {era: [t["name"] for t in ts] for era, ts in eras.items()},
        "genre_clusters": {g: [t["name"] for t in ts] for g, ts in genres.items()},
    }

    out_path = os.path.join(stems_dir, "temporal_genome.json")
    with open(out_path, 'w') as f:
        json.dump(enhanced, f, indent=2)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*80}")

if __name__ == "__main__":
    stems_dir = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLAUDES_EARS_STEMS", os.path.join("stems", "htdemucs"))
    build_temporal_genome(stems_dir)
