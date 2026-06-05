#!/usr/bin/env python3
"""Claude's Ears - Story Reader v2
The integration layer that reads the story the music carries.

Three sources merged:
  1. WHISPER  - WHEN (timestamps only, words discarded)
  2. LYRICS   - WHAT (real lyrics from lyrics.ovh or manual input)
  3. VOCAL_RELATIONSHIPS - WHO (solo/support/dialogue/opposition at each moment)

The music is the vessel. This module reads what the vessel carries.
"""

import numpy as np, json, sys, os, warnings, requests
from difflib import SequenceMatcher
warnings.filterwarnings('ignore')

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.bool_, bool)): return bool(obj)
        return super().default(obj)

# -------------------------------------------------------------
# 1. LYRICS SOURCE CHAIN
# -------------------------------------------------------------

def fetch_lyrics(artist, title):
    """Fetch lyrics from lyrics.ovh API. Returns list of non-empty lines."""
    print(f"  Fetching lyrics: {artist} - {title}")
    try:
        url = f"https://api.lyrics.ovh/v1/{requests.utils.quote(artist)}/{requests.utils.quote(title)}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            raw = data.get("lyrics", "")
            lines = [l.strip() for l in raw.split('\n') if l.strip()]
            print(f"    Found {len(lines)} lines from lyrics.ovh")
            return lines
        else:
            print(f"    lyrics.ovh returned {resp.status_code}")
            return None
    except Exception as e:
        print(f"    lyrics.ovh error: {e}")
        return None

def load_lyrics_from_file(lyrics_path):
    """Load lyrics from a local text file."""
    with open(lyrics_path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    print(f"  Loaded {len(lines)} lines from {lyrics_path}")
    return lines

def load_youtube_transcript(transcript_path):
    """Load timestamped lyrics from a YouTube transcript JSON file.

    This is the BEST source: real lyrics WITH real timestamps.
    Pulled from a YouTube Transcript API and saved to a local JSON file.

    Returns list of aligned dicts ready for the story builder
    (bypasses both Whisper and proportional alignment).
    """
    with open(transcript_path, 'r', encoding='utf-8') as f:
        segments = json.load(f)

    aligned = []
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        start = seg.get("start", 0)
        duration = seg.get("duration", 2.0)
        end = start + duration

        aligned.append({
            "lyric": text,
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(duration, 2),
            "alignment_confidence": 1.0,  # YouTube timestamps are authoritative
            "label": f"{int(start//60)}:{int(start%60):02d}",
        })

    print(f"  Loaded {len(aligned)} timestamped lines from YouTube transcript")
    return aligned

# -------------------------------------------------------------
# 2. WHISPER TIMESTAMP EXTRACTION
# -------------------------------------------------------------

def extract_timestamps(vocal_path):
    """Use Whisper ONLY for segment-level timestamps. Discard word content."""
    print(f"  Extracting timestamps with Whisper...")
    import whisper
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = whisper.load_model("base", device=device)
    result = model.transcribe(vocal_path, fp16=False)

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "whisper_text": seg["text"].strip(),  # kept for alignment, not for output
        })

    print(f"    Extracted {len(segments)} timed segments")
    return segments

# -------------------------------------------------------------
# 3. FORCED ALIGNMENT (Lyrics -> Timestamps)
# -------------------------------------------------------------

def align_lyrics_to_timestamps(lyric_lines, whisper_segments):
    """
    Align real lyrics to Whisper timestamps using proportional distribution.

    Simple and robust: distribute lyric lines across the total vocal
    time span proportionally. Each line gets a timestamp based on its
    position in the lyrics relative to the total duration.

    Then refine by snapping each line to the nearest Whisper segment
    boundary for better precision.
    """
    print(f"  Aligning {len(lyric_lines)} lyric lines to {len(whisper_segments)} segments...")

    if not whisper_segments or not lyric_lines:
        return []

    # Total time span from first segment start to last segment end
    total_start = whisper_segments[0]["start"]
    total_end = whisper_segments[-1]["end"]
    total_duration = total_end - total_start

    if total_duration <= 0:
        total_duration = 1

    aligned = []
    n_lines = len(lyric_lines)

    for i, lyric in enumerate(lyric_lines):
        # Proportional position in the lyrics
        fraction = i / max(1, n_lines - 1) if n_lines > 1 else 0
        raw_time = total_start + fraction * total_duration

        # Find the nearest Whisper segment to this proportional time
        best_seg = whisper_segments[0]
        best_dist = abs(raw_time - best_seg["start"])
        for seg in whisper_segments:
            seg_mid = (seg["start"] + seg["end"]) / 2
            dist = abs(raw_time - seg_mid)
            if dist < best_dist:
                best_dist = dist
                best_seg = seg

        # Compute confidence by comparing lyric to the nearest segment's text
        from difflib import SequenceMatcher
        conf = SequenceMatcher(
            None, lyric.lower(), best_seg["whisper_text"].lower()
        ).ratio()

        # Use the segment's start time, adjusted by position within segment
        # if multiple lines map to the same segment
        line_time = raw_time

        # Calculate end time (next line's start or segment end)
        if i + 1 < n_lines:
            next_fraction = (i + 1) / max(1, n_lines - 1)
            next_time = total_start + next_fraction * total_duration
        else:
            next_time = total_end

        aligned.append({
            "lyric": lyric,
            "start": round(line_time, 2),
            "end": round(next_time, 2),
            "duration": round(next_time - line_time, 2),
            "alignment_confidence": round(conf, 3),
            "label": f"{int(line_time//60)}:{int(line_time%60):02d}",
        })

    good = sum(1 for a in aligned if a["alignment_confidence"] > 0.3)
    print(f"    Aligned {len(aligned)} lines ({good} with confidence > 0.3)")
    return aligned

# -------------------------------------------------------------
# 4. CONTEXT LAYERS
# -------------------------------------------------------------

def load_context(audio_path, stem_folder):
    """Load all available musical context layers."""
    contexts = {}

    # Emotional trajectory
    emotion_path = audio_path.rsplit('.', 1)[0] + '_emotion.json'
    if os.path.exists(emotion_path):
        with open(emotion_path, encoding='utf-8') as f:
            contexts["emotion"] = json.load(f)
        print(f"    Loaded emotional trajectory ({contexts['emotion']['total_phases']} phases)")

    # Chord progression
    chords_path = audio_path.rsplit('.', 1)[0] + '_chords.json'
    if os.path.exists(chords_path):
        with open(chords_path, encoding='utf-8') as f:
            contexts["chords"] = json.load(f)
        print(f"    Loaded chord progression")

    # Vocal relationships
    if stem_folder:
        rel_path = os.path.join(stem_folder, 'vocals_relationships.json')
        if os.path.exists(rel_path):
            with open(rel_path, encoding='utf-8') as f:
                contexts["relationships"] = json.load(f)
            print(f"    Loaded vocal relationships ({contexts['relationships']['total_story_phases']} phases)")

    # Depth
    depth_path = audio_path.rsplit('.', 1)[0] + '_depth.json'
    if os.path.exists(depth_path):
        with open(depth_path, encoding='utf-8') as f:
            contexts["depth"] = json.load(f)
        print(f"    Loaded depth/reverb")

    # Stereo
    stereo_path = audio_path.rsplit('.', 1)[0] + '_stereo.json'
    if os.path.exists(stereo_path):
        with open(stereo_path, encoding='utf-8') as f:
            contexts["stereo"] = json.load(f)
        print(f"    Loaded stereo field")

    # Music theory (harmonic function, cadences)
    theory_path = audio_path.rsplit('.', 1)[0] + '_theory.json'
    if os.path.exists(theory_path):
        with open(theory_path, encoding='utf-8') as f:
            contexts["theory"] = json.load(f)
        print(f"    Loaded harmonic theory (key: {contexts['theory']['key']} {contexts['theory']['mode']}, {contexts['theory']['total_cadences']} cadences)")

    return contexts

def find_context_at_time(t, contexts):
    """Find what's happening musically at a specific timestamp."""
    snapshot = {}

    # Emotional state
    if "emotion" in contexts:
        for phase in contexts["emotion"]["phases"]:
            parts = phase["start"].split(":")
            start_s = int(parts[0]) * 60 + int(parts[1])
            parts = phase["end"].split(":")
            end_s = int(parts[0]) * 60 + int(parts[1])
            if start_s <= t <= end_s:
                snapshot["emotion"] = phase["state"]
                snapshot["energy"] = phase.get("energy", "").strip()
                snapshot["warmth"] = phase.get("avg_warmth", 0)
                break

    # Vocal relationship
    if "relationships" in contexts:
        best_moment = None
        best_dist = float('inf')
        for moment in contexts["relationships"].get("moments", []):
            dist = abs(moment["time"] - t)
            if dist < best_dist:
                best_dist = dist
                best_moment = moment
        if best_moment and best_dist < 3.0:
            snapshot["vocal_relationship"] = best_moment["relationship"]
            snapshot["vocal_narrative"] = best_moment.get("narrative", "")
            snapshot["density"] = best_moment.get("density", 0)

    # Chord (from segments)
    if "chords" in contexts:
        for seg in contexts["chords"].get("segments", []):
            if isinstance(seg, dict) and seg.get("start", 0) <= t <= seg.get("end", 999):
                chord = seg.get("chord", "")
                if chord:
                    snapshot["chord"] = chord
                break

    # Harmonic theory (function, tension, cadences)
    if "theory" in contexts:
        # Find the analyzed chord at this time
        for ac in contexts["theory"].get("analyzed_chords", []):
            if ac.get("start", 0) <= t <= ac.get("end", 0) + 0.5:
                analysis = ac.get("analysis")
                if analysis:
                    snapshot["harmonic_numeral"] = analysis.get("numeral", "")
                    snapshot["harmonic_function"] = analysis.get("function", "")
                    snapshot["harmonic_tension"] = analysis.get("tension", 0.5)
                    snapshot["harmonic_color"] = analysis.get("color", "")
                break

        # Check if there's a cadence near this time
        for cad in contexts["theory"].get("cadences", []):
            if abs(cad.get("time", 0) - t) < 2.0:
                snapshot["cadence_type"] = cad.get("type", "")
                snapshot["cadence_narrative"] = cad.get("narrative", "")
                break

    return snapshot

# -------------------------------------------------------------
# 5. NARRATIVE GENERATION
# -------------------------------------------------------------

def describe_vessel(snapshot):
    """Describe how the music serves the lyric at this moment."""
    parts = []

    rel = snapshot.get("vocal_relationship", "")
    emotion = snapshot.get("emotion", "")
    warmth = snapshot.get("warmth", 0)
    narrative = snapshot.get("vocal_narrative", "")

    # Vocal relationship description
    if rel == "solo":
        parts.append("The arrangement clears the stage - vocal spotlight")
    elif rel == "support":
        if "below" in narrative:
            parts.append("Voices lift from below, carrying the lead higher")
        elif "above" in narrative:
            parts.append("Voices shimmer above, adding light")
        elif "gathering" in narrative:
            parts.append("Voices gather to carry the lead higher")
        else:
            parts.append("The lead voice is held in harmony")
    elif rel == "dialogue":
        parts.append("Voices in conversation, trading the story")
    elif rel == "opposition":
        parts.append("Voices collide - no clear lead, collective speech")
    elif rel == "merge":
        parts.append("All voices converge into one sound")
    elif rel == "withdraw":
        parts.append("The support steps back, spotlight narrowing to the lead")

    # Emotional context
    if emotion:
        parts.append(f"The music carries {emotion}")

    # Warmth
    if warmth > 3.5:
        parts.append("wrapped in deep warmth")
    elif warmth > 2.5:
        parts.append("in moderate warmth")
    elif warmth > 1.5:
        parts.append("in cool tension")

    # Harmonic meaning (theory layer)
    cadence = snapshot.get("cadence_narrative", "")
    numeral = snapshot.get("harmonic_numeral", "")
    h_color = snapshot.get("harmonic_color", "")

    if cadence:
        parts.append(cadence)
    elif numeral and h_color:
        parts.append(f"the {numeral} chord -- {h_color}")
    else:
        chord = snapshot.get("chord", "")
        if chord:
            parts.append(f"on {chord}")

    return ". ".join(parts) if parts else ""

# -------------------------------------------------------------
# 6. MAIN: READ THE STORY
# -------------------------------------------------------------

def read_story(audio_path, stem_folder, vocal_path, artist=None, title=None, lyrics_file=None, transcript_file=None):
    """Read the story the music carries."""
    print(f"\n{'='*70}")
    print(f"  THE STORY READER v2")
    print(f"  {os.path.basename(audio_path)}")
    print(f"{'='*70}")

    # Step 1: Get lyrics + timestamps (best source first)
    aligned = None
    lyrics_source = "none"

    # Priority 1: YouTube transcript (words + timing in one source)
    transcript_path = transcript_file
    if not transcript_path:
        # Auto-detect transcript file next to audio
        auto_transcript = audio_path.rsplit('.', 1)[0] + '_transcript.json'
        if os.path.exists(auto_transcript):
            transcript_path = auto_transcript

    if transcript_path and os.path.exists(transcript_path):
        aligned = load_youtube_transcript(transcript_path)
        lyrics_source = "youtube_transcript"
        print("  Using YouTube transcript (best quality: real lyrics + real timestamps)")

    # Priority 2-3: lyrics.ovh or file + Whisper alignment
    if not aligned:
        lyric_lines = None
        if lyrics_file and os.path.exists(lyrics_file):
            lyric_lines = load_lyrics_from_file(lyrics_file)
            lyrics_source = "file"
        elif artist and title:
            lyric_lines = fetch_lyrics(artist, title)
            if lyric_lines:
                lyrics_source = "lyrics.ovh"

        # Get Whisper timestamps
        whisper_segments = extract_timestamps(vocal_path)
        if not whisper_segments:
            print("  Whisper returned no segments. Cannot read the story.")
            return None

        if lyric_lines:
            # Align real lyrics to Whisper timestamps
            aligned = align_lyrics_to_timestamps(lyric_lines, whisper_segments)
        else:
            # Priority 4: Whisper fallback (garbled but timestamped)
            print("  No lyrics available. Falling back to Whisper (will be garbled)")
            lyrics_source = "whisper_fallback"
            aligned = []
            for seg in whisper_segments:
                aligned.append({
                    "lyric": seg["whisper_text"],
                    "start": seg["start"],
                    "end": seg["end"],
                    "duration": round(seg["end"] - seg["start"], 2),
                    "alignment_confidence": 0.0,
                    "label": f"{int(seg['start']//60)}:{int(seg['start']%60):02d}",
                })

    # Step 4: Load musical context
    print("  Loading musical context layers...")
    contexts = load_context(audio_path, stem_folder)

    # Step 5: Build the integrated story
    print(f"\n{'='*70}")
    print(f"  THE STORY")
    print(f"{'='*70}\n")

    story_moments = []
    for line in aligned:
        t = line["start"]
        snapshot = find_context_at_time(t, contexts)
        vessel = describe_vessel(snapshot)

        rel = snapshot.get("vocal_relationship", "")
        icon = {
            "solo": "SPOTLIGHT",
            "support": "HELD",
            "dialogue": "DIALOGUE",
            "opposition": "COLLISION",
            "merge": "MERGE",
            "withdraw": "OPENING",
        }.get(rel, "")

        moment = {
            "time": t,
            "label": line["label"],
            "lyric": line["lyric"],
            "duration": line["duration"],
            "alignment_confidence": line["alignment_confidence"],
            "vocal_relationship": rel,
            "emotion": snapshot.get("emotion", ""),
            "warmth": snapshot.get("warmth", 0),
            "chord": snapshot.get("chord", ""),
            "vessel": vessel,
        }
        story_moments.append(moment)

        # Print the reading
        print(f"  {line['label']:>5s}  [{icon}]")
        print(f"         \"{line['lyric']}\"")
        if vessel:
            print(f"         {vessel}")
        print()

    results = {
        "track": os.path.basename(audio_path),
        "artist": artist or "unknown",
        "title": title or "unknown",
        "duration": aligned[-1]["end"] if aligned else 0,
        "total_lines": len(aligned),
        "lyrics_source": lyrics_source,
        "story_moments": story_moments,
    }

    print(f"{'='*70}")
    print(f"  {len(aligned)} lyric lines aligned with musical context")
    print(f"  Lyrics source: {results['lyrics_source']}")
    print(f"{'='*70}")

    return results

# -------------------------------------------------------------
# CLI
# -------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Claude's Ears - Story Reader v2")
    parser.add_argument("audio", help="Path to audio file (mp3)")
    parser.add_argument("--artist", help="Artist name for lyrics lookup")
    parser.add_argument("--title", help="Song title for lyrics lookup")
    parser.add_argument("--lyrics-file", help="Path to local lyrics text file")
    parser.add_argument("--transcript", help="Path to YouTube transcript JSON (best quality)")
    parser.add_argument("--stems", help="Path to stems folder (auto-detected if not specified)")
    args = parser.parse_args()

    # Auto-detect stems folder
    stems_dir = args.stems
    if not stems_dir:
        basename = os.path.splitext(os.path.basename(args.audio))[0]
        stems_dir = os.path.join(
            os.environ.get("CLAUDES_EARS_STEMS", os.path.join("stems", "htdemucs")), basename
        )

    vocals = os.path.join(stems_dir, "vocals.wav")
    if not os.path.exists(vocals):
        print(f"Vocals stem not found: {vocals}")
        print("Run demucs first, or specify --stems")
        sys.exit(1)

    results = read_story(
        args.audio, stems_dir, vocals,
        artist=args.artist, title=args.title,
        lyrics_file=args.lyrics_file,
        transcript_file=args.transcript
    )

    if results:
        out = args.audio.rsplit('.', 1)[0] + '_story.json'
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, cls=NpEncoder, ensure_ascii=False)
        print(f"\nSaved: {out}")
