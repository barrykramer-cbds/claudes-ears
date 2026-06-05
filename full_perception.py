#!/usr/bin/env python3
"""Claude's Ears - Full Perception Pipeline
Single entry point: give it an audio file, get everything.

Runs 21 orchestrated modules in correct order with error handling.
Three modules are standalone (run on demand, not wired here):
  - ai_detector.py     (per-track AI-likelihood scorer; investigative)
  - version_compare.py (needs TWO versions: studio vs live)
  - semantic_lyrics.py (prints lyric analysis; no JSON artifact yet)

Usage:
  python full_perception.py "path/to/audio.mp3"
  python full_perception.py "path/to/audio.mp3" --skip-demucs  (if stems exist)
  python full_perception.py --batch "path/to/music/folder"     (process all mp3s)

Paths are resolved relative to this file. Override stem/music roots with
env vars CLAUDES_EARS_STEMS and CLAUDES_EARS_MUSIC if your layout differs.
"""

import subprocess, sys, os, glob, json, time

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
STEMS_DIR = os.path.join(WORKSPACE, "stems", "htdemucs")

def run_step(name, cmd, optional=False):
    """Run a pipeline step with error handling."""
    print(f"\n{'-'*60}")
    print(f"  > {name}")
    print(f"{'-'*60}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=False, timeout=600)
        if result.returncode != 0:
            print(f"  ! {name} returned code {result.returncode}")
            if not optional:
                print(f"  -> Continuing anyway...")
        else:
            print(f"  [ok] {name} complete")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  ! {name} timed out (600s)")
        return False
    except Exception as e:
        print(f"  [x] {name} error: {e}")
        return False

def get_stem_folder(audio_path):
    """Derive the stem folder name from the audio file path."""
    basename = os.path.splitext(os.path.basename(audio_path))[0]
    return os.path.join(STEMS_DIR, basename)

def parse_artist_title(audio_path):
    """Derive (artist, title) from an 'Artist - Title.mp3' filename.

    Matches the canonical yt-dlp naming used to build the library.
    Returns (None, None) when the filename doesn't follow the pattern,
    in which case lyric-dependent steps fall back to other sources.
    """
    base = os.path.splitext(os.path.basename(audio_path))[0]
    if " - " in base:
        artist, title = base.split(" - ", 1)
        return artist.strip(), title.strip()
    return None, None

def full_perception(audio_path, skip_demucs=False):
    """Run the complete perception pipeline on a single audio file."""
    print(f"\n{'='*60}")
    print(f"  CLAUDE'S EARS - FULL PERCEPTION PIPELINE")
    print(f"  {os.path.basename(audio_path)}")
    print(f"{'='*60}")

    start_time = time.time()
    stem_folder = get_stem_folder(audio_path)
    py = sys.executable
    artist, title = parse_artist_title(audio_path)

    results = {}

    # Phase 1: Stem Separation
    if not skip_demucs:
        results["demucs"] = run_step("Stem Separation (demucs GPU)",
            f'"{py}" "{WORKSPACE}/run_demucs.py" "{audio_path}"')
    else:
        print("\n  [skip] Skipping demucs (--skip-demucs)")
        results["demucs"] = True

    # Verify stems exist
    if not os.path.exists(stem_folder):
        print(f"\n  [x] Stem folder not found: {stem_folder}")
        print(f"    Check if demucs named it differently")
        # Try to find it
        basename = os.path.splitext(os.path.basename(audio_path))[0]
        matches = glob.glob(os.path.join(STEMS_DIR, f"*{basename[:20]}*"))
        if matches:
            stem_folder = matches[0]
            print(f"    Found: {stem_folder}")
        else:
            print(f"    No matches found. Aborting stem-dependent steps.")
            stem_folder = None

    # Phase 2: Stem Analysis
    if stem_folder:
        results["stems"] = run_step("Stem Analysis",
            f'"{py}" "{WORKSPACE}/analyze_stems.py" "{stem_folder}"')

        vocals_path = os.path.join(stem_folder, "vocals.wav")
        drums_path = os.path.join(stem_folder, "drums.wav")

        results["vocal_layers"] = run_step("Vocal Layers",
            f'"{py}" "{WORKSPACE}/vocal_layers.py" "{vocals_path}"')

        results["vocal_intervals"] = run_step("Vocal Intervals",
            f'"{py}" "{WORKSPACE}/vocal_intervals.py" "{vocals_path}"')

        results["groove"] = run_step("Groove Timing",
            f'"{py}" "{WORKSPACE}/groove_timing.py" "{drums_path}"')

        results["freq_interaction"] = run_step("Frequency Interaction",
            f'"{py}" "{WORKSPACE}/freq_interaction.py" "{stem_folder}"')

    # Phase 2b: Deeper Stem Analysis
    if stem_folder:
        other_path = os.path.join(stem_folder, "other.wav")
        vocals_path_2 = os.path.join(stem_folder, "vocals.wav")

        results["timbral"] = run_step("Timbral Decomposition (other stem)",
            f'"{py}" "{WORKSPACE}/timbral_decomposition.py" "{other_path}" 4', optional=True)

        results["vocal_narrative"] = run_step("Vocal Narrative (lead vs chorus)",
            f'"{py}" "{WORKSPACE}/vocal_narrative.py" "{vocals_path_2}"', optional=True)

        results["vocal_relationships"] = run_step("Vocal Relationships (story between voices)",
            f'"{py}" "{WORKSPACE}/vocal_relationships.py" "{vocals_path_2}"', optional=True)

    # Phase 2c: Register Tracking
    if stem_folder:
        vocals_path_3 = os.path.join(stem_folder, "vocals.wav")
        results["register"] = run_step("Register Tracking (chest/head/falsetto)",
            f'"{py}" "{WORKSPACE}/register_tracking.py" "{vocals_path_3}"', optional=True)

    # Phase 2d: Breath Detection
    if stem_folder:
        vocals_path_4 = os.path.join(stem_folder, "vocals.wav")
        results["breath"] = run_step("Breath Detection (physical presence)",
            f'"{py}" "{WORKSPACE}/breath_detection.py" "{vocals_path_4}"', optional=True)

    # Phase 3: Full-Mix Analysis
    results["stereo"] = run_step("Stereo Field",
        f'"{py}" "{WORKSPACE}/stereo_field.py" "{audio_path}"')

    results["temporal"] = run_step("Temporal Segmentation",
        f'"{py}" "{WORKSPACE}/temporal_segmentation.py" "{audio_path}" 15 5')

    results["depth"] = run_step("Depth/Reverb",
        f'"{py}" "{WORKSPACE}/depth_reverb.py" "{audio_path}"')

    results["chords"] = run_step("Chord Progression",
        f'"{py}" "{WORKSPACE}/chord_progression.py" "{audio_path}"')

    # Phase 4: Derived Analysis
    temporal_json = audio_path.rsplit('.', 1)[0] + '_temporal.json'
    if os.path.exists(temporal_json):
        results["emotion"] = run_step("Emotional Trajectory",
            f'"{py}" "{WORKSPACE}/emotional_trajectory.py" "{temporal_json}"')
    else:
        print(f"\n  [skip] Skipping Emotional Trajectory (no temporal JSON)")

    # Phase 4b: Harmonic Rhythm (rate of chord change)
    chords_json = audio_path.rsplit('.', 1)[0] + '_chords.json'
    if os.path.exists(chords_json):
        results["harmonic_rhythm"] = run_step("Harmonic Rhythm (rate of chord change)",
            f'"{py}" "{WORKSPACE}/harmonic_rhythm.py" "{chords_json}"', optional=True)

    # Phase 4c: Music Theory (key, Roman numerals, cadences)
    # Reads the same _chords.json as harmonic_rhythm; produces _theory.json,
    # which the Story Reader consumes for harmonic meaning.
    if os.path.exists(chords_json):
        results["music_theory"] = run_step("Music Theory (key, Roman numerals, cadences)",
            f'"{py}" "{WORKSPACE}/music_theory.py" "{chords_json}"', optional=True)

    # Phase 4d: Story Reader (final per-track step)
    # Integrates lyrics + emotion + vocal relationships + chords + theory.
    # Auto-detects a <track>_transcript.json next to the audio for best
    # quality; otherwise tries lyrics.ovh via artist/title, then falls back
    # to Whisper timestamps. Heavy (may invoke Whisper) -> optional.
    if stem_folder:
        story_cmd = f'"{py}" "{WORKSPACE}/story_reader.py" "{audio_path}" --stems "{stem_folder}"'
        if artist and title:
            story_cmd += f' --artist "{artist}" --title "{title}"'
        results["story"] = run_step("Story Reader (lyrics + music integration)",
            story_cmd, optional=True)

    # Phase 5: Library-Level Analysis
    results["genome"] = run_step("Genome Map",
        f'"{py}" "{WORKSPACE}/genome_map.py"')

    results["temporal_genome"] = run_step("Temporal Genome",
        f'"{py}" "{WORKSPACE}/temporal_genome.py"', optional=True)

    # Summary
    elapsed = time.time() - start_time
    success = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  {success}/{total} steps succeeded")
    print(f"  Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"{'='*60}")

    for step, ok in results.items():
        status = "[ok]" if ok else "[x]"
        print(f"  {status} {step}")

    return results

def batch_process(music_dir):
    """Process all MP3 files in a directory."""
    mp3s = glob.glob(os.path.join(music_dir, "*.mp3"))
    print(f"\n{'='*60}")
    print(f"  BATCH PROCESSING: {len(mp3s)} tracks")
    print(f"  Directory: {music_dir}")
    print(f"{'='*60}")

    for i, mp3 in enumerate(mp3s):
        basename = os.path.basename(mp3)
        stem_folder = get_stem_folder(mp3)

        # Skip if already fully analyzed
        if os.path.exists(stem_folder) and os.path.exists(os.path.join(stem_folder, "stem_analysis.json")):
            emotion_json = mp3.rsplit('.', 1)[0] + '_emotion.json'
            if os.path.exists(emotion_json):
                print(f"\n  [{i+1}/{len(mp3s)}] SKIP (already analyzed): {basename}")
                continue

        print(f"\n  [{i+1}/{len(mp3s)}] Processing: {basename}")
        skip = os.path.exists(stem_folder) and len(glob.glob(os.path.join(stem_folder, "*.wav"))) >= 4
        full_perception(mp3, skip_demucs=skip)

    # Final genome map across all tracks
    print(f"\n  Running final genome map across all tracks...")
    py = sys.executable
    run_step("Final Genome Map", f'"{py}" "{WORKSPACE}/genome_map.py"')
    run_step("Final Temporal Genome", f'"{py}" "{WORKSPACE}/temporal_genome.py"', optional=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  python full_perception.py <audio.mp3>")
        print(f"  python full_perception.py <audio.mp3> --skip-demucs")
        print(f"  python full_perception.py --batch <music_folder>")
        sys.exit(1)

    if sys.argv[1] == "--batch":
        if len(sys.argv) < 3:
            batch_process(os.environ.get("CLAUDES_EARS_MUSIC", "music"))
        else:
            batch_process(sys.argv[2])
    else:
        skip = "--skip-demucs" in sys.argv
        full_perception(sys.argv[1], skip_demucs=skip)
