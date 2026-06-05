#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude's Ears - Music Theory Interpreter
Adds harmonic MEANING to chord data.

Not just "Am" but "the vi chord -- relative minor, melancholic."
Not just "Am -> C" but "deceptive motion -- the harmony refuses to
go where you expect and opens into something brighter."

The theory layer sits between measurement and interpretation.
The chord_progression module measures WHAT.
This module interprets WHY it matters.

Input: chord progression JSON from chord_progression.py
Output: harmonic analysis with function, tension, cadences

The theory serves the story. Every resolution and suspension
exists to make a specific lyric land at a specific moment.
"""

import json, sys, os, re, numpy as np

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.bool_, bool)): return bool(obj)
        return super().default(obj)

# --- MUSIC THEORY CONSTANTS ---

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
ENHARMONIC = {'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#',
              'Cb': 'B', 'E#': 'F', 'B#': 'C'}

# Scale degrees in semitones from root
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]

# Roman numeral labels for each scale degree (major key)
MAJOR_NUMERALS = ['I', 'ii', 'iii', 'IV', 'V', 'vi', 'vii']
MINOR_NUMERALS = ['i', 'ii', 'III', 'iv', 'v', 'VI', 'VII']

# Harmonic function categories
FUNCTION_MAP = {
    'I': 'tonic',      'i': 'tonic',
    'ii': 'predominant', 'II': 'predominant',
    'iii': 'tonic',     'III': 'tonic',
    'IV': 'subdominant', 'iv': 'subdominant',
    'V': 'dominant',    'v': 'dominant',
    'vi': 'tonic',      'VI': 'subdominant',
    'vii': 'dominant',  'VII': 'subtonic',
}

# Tension values (0 = stable/resolved, 1 = maximum tension)
TENSION_MAP = {
    'I': 0.0,  'i': 0.1,
    'ii': 0.4, 'II': 0.5,
    'iii': 0.3, 'III': 0.3,
    'IV': 0.3, 'iv': 0.4,
    'V': 0.7,  'v': 0.5,
    'vi': 0.2, 'VI': 0.3,
    'vii': 0.8, 'VII': 0.6,
}

# Emotional color for each degree
COLOR_MAP = {
    'I': 'home, resolution, arrival',
    'i': 'dark home, minor resolution',
    'ii': 'gentle yearning, pre-departure',
    'II': 'bright yearning',
    'iii': 'bittersweet, contemplative',
    'III': 'relative brightness, opening',
    'IV': 'warmth, expansion, departure',
    'iv': 'dark warmth, minor expansion',
    'V': 'tension, expectation, pull toward home',
    'v': 'uncertain pull, weakened expectation',
    'vi': 'melancholy, the shadow of home',
    'VI': 'surprise brightness, deceptive warmth',
    'vii': 'urgent tension, leading edge',
    'VII': 'flat seventh, bluesy departure',
}

def parse_chord_root(chord_label):
    """Extract root note from a chord label like 'Am7', 'C#maj', 'Bbdim'."""
    if not chord_label or chord_label in ('N', 'X', ''):
        return None

    # Match root: letter + optional sharp/flat
    m = re.match(r'^([A-G][#b]?)', chord_label)
    if not m:
        return None

    root = m.group(1)
    # Normalize enharmonics
    root = ENHARMONIC.get(root, root)
    return root

def parse_chord_quality(chord_label):
    """Determine if chord is major, minor, diminished, augmented, etc."""
    if not chord_label:
        return 'unknown'

    label = chord_label.lower()
    root_match = re.match(r'^[a-g][#b]?', label)
    if not root_match:
        return 'unknown'
    quality_part = label[root_match.end():]

    if 'dim' in quality_part or 'o' in quality_part:
        return 'diminished'
    elif 'aug' in quality_part or '+' in quality_part:
        return 'augmented'
    elif 'min' in quality_part or 'm' in quality_part[:2]:
        return 'minor'
    elif 'maj' in quality_part or quality_part == '' or quality_part.startswith('7') or quality_part.startswith('9'):
        return 'major'
    elif 'sus' in quality_part:
        return 'suspended'
    else:
        return 'major'  # default

def note_to_semitone(note):
    """Convert note name to semitone number (C=0)."""
    if note in NOTE_NAMES:
        return NOTE_NAMES.index(note)
    note = ENHARMONIC.get(note, note)
    if note in NOTE_NAMES:
        return NOTE_NAMES.index(note)
    return 0

def detect_key(chord_segments):
    """
    Estimate the key using Krumhansl-Schmuckler key-finding algorithm.
    Uses chord root distribution weighted by duration.
    """
    # Count weighted occurrences of each pitch class
    pitch_weights = np.zeros(12)
    for seg in chord_segments:
        root = parse_chord_root(seg.get('chord', ''))
        if root:
            semitone = note_to_semitone(root)
            duration = seg.get('end', 0) - seg.get('start', 0)
            pitch_weights[semitone] += max(duration, 0.1)

    if np.sum(pitch_weights) == 0:
        return 'C', 'major', 0.0

    # Krumhansl-Schmuckler profiles
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    best_key = 'C'
    best_mode = 'major'
    best_corr = -1

    for shift in range(12):
        shifted = np.roll(pitch_weights, -shift)

        corr_major = float(np.corrcoef(shifted, major_profile)[0, 1])
        corr_minor = float(np.corrcoef(shifted, minor_profile)[0, 1])

        if corr_major > best_corr:
            best_corr = corr_major
            best_key = NOTE_NAMES[shift]
            best_mode = 'major'
        if corr_minor > best_corr:
            best_corr = corr_minor
            best_key = NOTE_NAMES[shift]
            best_mode = 'minor'

    return best_key, best_mode, round(best_corr, 3)

def chord_to_roman(chord_label, key_root, key_mode):
    """Convert a chord label to Roman numeral analysis relative to key."""
    root = parse_chord_root(chord_label)
    if not root:
        return None

    quality = parse_chord_quality(chord_label)
    key_semitone = note_to_semitone(key_root)
    chord_semitone = note_to_semitone(root)

    # Interval from key root
    interval = (chord_semitone - key_semitone) % 12

    # Find closest scale degree
    scale = MAJOR_SCALE if key_mode == 'major' else MINOR_SCALE
    numerals = MAJOR_NUMERALS if key_mode == 'major' else MINOR_NUMERALS

    best_degree = 0
    best_dist = 12
    for i, s in enumerate(scale):
        dist = abs(interval - s)
        if dist < best_dist:
            best_dist = dist
            best_degree = i

    if best_dist > 1:
        # Chromatic chord -- not in the key
        roman = f"[{root}]"
        return {
            'numeral': roman,
            'function': 'chromatic',
            'tension': 0.6,
            'color': 'outside the key, chromatic color',
            'is_chromatic': True,
        }

    roman = numerals[best_degree]

    # Adjust for quality mismatch (e.g., major chord on a minor degree)
    if quality == 'major' and roman.islower() and roman != 'vii':
        roman = roman.upper()  # borrowed chord
    elif quality == 'minor' and roman.isupper() and roman != 'I':
        roman = roman.lower()  # borrowed chord

    return {
        'numeral': roman,
        'function': FUNCTION_MAP.get(roman, 'unknown'),
        'tension': TENSION_MAP.get(roman, 0.5),
        'color': COLOR_MAP.get(roman, 'unknown harmonic color'),
        'is_chromatic': False,
    }

def detect_cadences(analyzed_chords):
    """Detect cadences -- the punctuation of harmony."""
    cadences = []

    for i in range(1, len(analyzed_chords)):
        prev = analyzed_chords[i-1]
        curr = analyzed_chords[i]

        if not prev.get('analysis') or not curr.get('analysis'):
            continue

        pn = prev['analysis']['numeral']
        cn = curr['analysis']['numeral']

        cadence = None

        # Authentic cadence: V -> I (strongest resolution)
        if pn == 'V' and cn in ('I', 'i'):
            cadence = {'type': 'authentic', 'strength': 'strong',
                       'narrative': 'resolution -- the harmony arrives home'}

        # Plagal cadence: IV -> I (amen cadence, warm resolution)
        elif pn in ('IV', 'iv') and cn in ('I', 'i'):
            cadence = {'type': 'plagal', 'strength': 'gentle',
                       'narrative': 'warm resolution -- the amen cadence'}

        # Half cadence: anything -> V (tension, expectation)
        elif cn == 'V' and pn != 'V':
            cadence = {'type': 'half', 'strength': 'suspense',
                       'narrative': 'suspension -- the harmony pauses on tension'}

        # Deceptive cadence: V -> vi (expected resolution denied)
        elif pn == 'V' and cn in ('vi', 'VI'):
            cadence = {'type': 'deceptive', 'strength': 'surprise',
                       'narrative': 'deception -- expected home, got shadow instead'}

        # Minor resolution: v -> i or VII -> i
        elif cn == 'i' and pn in ('v', 'VII', 'V'):
            cadence = {'type': 'minor_authentic', 'strength': 'dark',
                       'narrative': 'dark resolution -- home is minor'}

        if cadence:
            cadence['time'] = curr.get('start', 0)
            cadence['label'] = curr.get('label', '')
            cadence['from'] = pn
            cadence['to'] = cn
            cadences.append(cadence)

    return cadences

def analyze_harmony(chords_path):
    """Full harmonic analysis of a chord progression."""
    print(f"  Music Theory: {os.path.basename(chords_path)}...")

    with open(chords_path, encoding='utf-8') as f:
        data = json.load(f)

    segments = data.get('segments', [])
    if not segments:
        print("    No chord segments found.")
        return None

    # Step 1: Detect key
    key_root, key_mode, key_confidence = detect_key(segments)
    print(f"    Key: {key_root} {key_mode} (confidence {key_confidence})")

    # Step 2: Analyze each chord
    analyzed = []
    for seg in segments:
        chord = seg.get('chord', '')
        analysis = chord_to_roman(chord, key_root, key_mode)

        entry = {
            'chord': chord,
            'start': seg.get('start', 0),
            'end': seg.get('end', 0),
            'label': f"{int(seg.get('start',0)//60)}:{int(seg.get('start',0)%60):02d}",
            'analysis': analysis,
        }
        analyzed.append(entry)

    # Step 3: Detect cadences
    cadences = detect_cadences(analyzed)
    print(f"    {len(cadences)} cadences detected")

    # Step 4: Compute tension curve
    tension_curve = []
    for a in analyzed:
        if a['analysis']:
            tension_curve.append({
                'time': a['start'],
                'tension': a['analysis']['tension'],
                'function': a['analysis']['function'],
            })

    # Step 5: Harmonic vocabulary richness
    numerals_used = set()
    for a in analyzed:
        if a['analysis']:
            numerals_used.add(a['analysis']['numeral'])

    chromatic_count = sum(1 for a in analyzed if a['analysis'] and a['analysis'].get('is_chromatic'))

    # Step 6: Cadence distribution
    cadence_types = {}
    for c in cadences:
        t = c['type']
        cadence_types[t] = cadence_types.get(t, 0) + 1

    results = {
        'key': key_root,
        'mode': key_mode,
        'key_confidence': key_confidence,
        'total_chords': len(segments),
        'unique_numerals': list(numerals_used),
        'harmonic_vocabulary_size': len(numerals_used),
        'chromatic_chords_pct': round(chromatic_count / max(len(segments), 1) * 100, 1),
        'total_cadences': len(cadences),
        'cadence_distribution': cadence_types,
        'cadences': cadences[:50],
        'analyzed_chords': analyzed[:200],
    }

    # Print summary
    print(f"\n  HARMONIC ANALYSIS")
    print(f"  {'='*60}")
    print(f"  Key: {key_root} {key_mode} (confidence {key_confidence})")
    print(f"  Vocabulary: {len(numerals_used)} unique chords: {', '.join(sorted(numerals_used))}")
    print(f"  Chromatic: {results['chromatic_chords_pct']}%")

    if cadences:
        print(f"\n  CADENCES ({len(cadences)} total):")
        for ct, count in sorted(cadence_types.items(), key=lambda x: -x[1]):
            print(f"    {ct:<20s}  {count}")
        print(f"\n  FIRST 10 CADENCES:")
        for c in cadences[:10]:
            print(f"    {c['label']:>5s}  {c['from']:>4s} -> {c['to']:<4s}  [{c['type']}] {c['narrative']}")

    print(f"  {'='*60}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python music_theory.py <track_chords.json>")
        sys.exit(1)

    results = analyze_harmony(sys.argv[1])
    if results:
        out = sys.argv[1].replace('_chords.json', '_theory.json')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, cls=NpEncoder)
        print(f"\nSaved: {out}")
