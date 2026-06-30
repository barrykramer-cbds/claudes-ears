"""Music-theory reading: key detection, Roman numerals, cadences from chord_progression output."""

from __future__ import annotations

import re
from typing import cast

import numpy as np

from claudes_ears._sanitize import sanitize

_NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_ENHARMONIC: dict[str, str] = {
    "Db": "C#",
    "Eb": "D#",
    "Fb": "E",
    "Gb": "F#",
    "Ab": "G#",
    "Bb": "A#",
    "Cb": "B",
    "E#": "F",
    "B#": "C",
}

_MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
_MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)
_MAJOR_NUMERALS = ("I", "ii", "iii", "IV", "V", "vi", "vii")
_MINOR_NUMERALS = ("i", "ii", "III", "iv", "v", "VI", "VII")

_FUNCTION_MAP: dict[str, str] = {
    "I": "tonic",
    "i": "tonic",
    "ii": "predominant",
    "II": "predominant",
    "iii": "tonic",
    "III": "tonic",
    "IV": "subdominant",
    "iv": "subdominant",
    "V": "dominant",
    "v": "dominant",
    "vi": "tonic",
    "VI": "subdominant",
    "vii": "dominant",
    "VII": "subtonic",
}

_TENSION_MAP: dict[str, float] = {
    "I": 0.0,
    "i": 0.1,
    "ii": 0.4,
    "II": 0.5,
    "iii": 0.3,
    "III": 0.3,
    "IV": 0.3,
    "iv": 0.4,
    "V": 0.7,
    "v": 0.5,
    "vi": 0.2,
    "VI": 0.3,
    "vii": 0.8,
    "VII": 0.6,
}

_COLOR_MAP: dict[str, str] = {
    "I": "home, resolution, arrival",
    "i": "dark home, minor resolution",
    "ii": "gentle yearning, pre-departure",
    "II": "bright yearning",
    "iii": "bittersweet, contemplative",
    "III": "relative brightness, opening",
    "IV": "warmth, expansion, departure",
    "iv": "dark warmth, minor expansion",
    "V": "tension, expectation, pull toward home",
    "v": "uncertain pull, weakened expectation",
    "vi": "melancholy, the shadow of home",
    "VI": "surprise brightness, deceptive warmth",
    "vii": "urgent tension, leading edge",
    "VII": "flat seventh, bluesy departure",
}

_MAJOR_KS = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_KS = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def _empty_result() -> dict[str, object]:
    return {
        "key": None,
        "mode": None,
        "key_confidence": None,
        "total_chords": 0,
        "unique_numerals": [],
        "harmonic_vocabulary_size": 0,
        "chromatic_chords_pct": 0.0,
        "total_cadences": 0,
        "cadence_distribution": {},
        "cadences": [],
        "analyzed_chords": [],
    }


def _parse_chord_root(chord_label: str) -> str | None:
    if not chord_label or chord_label in ("N", "X", "N.C.", ""):
        return None
    m = re.match(r"^([A-G][#b]?)", chord_label)
    if not m:
        return None
    root = m.group(1)
    return _ENHARMONIC.get(root, root)


def _parse_chord_quality(chord_label: str) -> str:
    """Return chord quality; tests major before minor to prevent maj7 misclassification."""
    if not chord_label:
        return "unknown"
    label = chord_label.lower()
    root_match = re.match(r"^[a-g][#b]?", label)
    if not root_match:
        return "unknown"
    q = label[root_match.end() :]
    # startswith avoids 'm' in 'maj7'[:2] matching the minor branch (ISSUE-003).
    if q.startswith(("dim", "o")):
        return "diminished"
    if q.startswith(("aug", "+")):
        return "augmented"
    if q.startswith("maj") or q == "" or (q and q[0] in "79"):
        return "major"
    if q.startswith(("min", "m")):
        return "minor"
    if q.startswith("sus"):
        return "suspended"
    return "major"


def _note_to_semitone(note: str) -> int:
    note = _ENHARMONIC.get(note, note)
    return list(_NOTE_NAMES).index(note) if note in _NOTE_NAMES else 0


def _detect_key(segments: list[object]) -> tuple[str, str, float]:
    """Krumhansl-Schmuckler key detection weighted by chord duration."""
    pitch_weights = np.zeros(12, dtype=np.float64)
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        root = _parse_chord_root(str(seg.get("chord", "")))
        if root:
            semitone = _note_to_semitone(root)
            duration = float(seg.get("end", 0)) - float(seg.get("start", 0))
            pitch_weights[semitone] += max(duration, 0.1)

    if np.sum(pitch_weights) == 0:
        return "C", "major", 0.0

    best_key, best_mode, best_corr = "C", "major", -1.0
    for shift in range(12):
        shifted = np.roll(pitch_weights, -shift)
        corr_major = float(np.corrcoef(shifted, _MAJOR_KS)[0, 1])
        corr_minor = float(np.corrcoef(shifted, _MINOR_KS)[0, 1])
        if corr_major > best_corr:
            best_corr, best_key, best_mode = corr_major, _NOTE_NAMES[shift], "major"
        if corr_minor > best_corr:
            best_corr, best_key, best_mode = corr_minor, _NOTE_NAMES[shift], "minor"

    # sanitize() converts NaN -> None at the boundary; no need to guard it here.
    return best_key, best_mode, round(best_corr, 3)


def _chord_to_roman(chord_label: str, key_root: str, key_mode: str) -> dict[str, object] | None:
    root = _parse_chord_root(chord_label)
    if not root:
        return None
    quality = _parse_chord_quality(chord_label)
    key_semitone = _note_to_semitone(key_root)
    chord_semitone = _note_to_semitone(root)
    interval = (chord_semitone - key_semitone) % 12
    scale = _MAJOR_SCALE if key_mode == "major" else _MINOR_SCALE
    numerals = _MAJOR_NUMERALS if key_mode == "major" else _MINOR_NUMERALS

    best_degree, best_dist = 0, 12
    for i, s in enumerate(scale):
        dist = abs(interval - s)
        if dist < best_dist:
            best_dist, best_degree = dist, i

    if best_dist > 1:
        return {
            "numeral": f"[{root}]",
            "function": "chromatic",
            "tension": 0.6,
            "color": "outside the key, chromatic color",
            "is_chromatic": True,
        }

    roman = numerals[best_degree]
    if quality == "major" and roman.islower() and roman != "vii":
        roman = roman.upper()
    elif quality == "minor" and roman.isupper() and roman != "I":
        roman = roman.lower()

    return {
        "numeral": roman,
        "function": _FUNCTION_MAP.get(roman, "unknown"),
        "tension": _TENSION_MAP.get(roman, 0.5),
        "color": _COLOR_MAP.get(roman, "unknown harmonic color"),
        "is_chromatic": False,
    }


def _detect_cadences(analyzed: list[dict[str, object]]) -> list[dict[str, object]]:
    cadences: list[dict[str, object]] = []
    for i in range(1, len(analyzed)):
        prev = analyzed[i - 1]
        curr = analyzed[i]
        if not prev.get("analysis") or not curr.get("analysis"):
            continue
        pn = str(cast("dict[str, object]", prev["analysis"])["numeral"])
        cn = str(cast("dict[str, object]", curr["analysis"])["numeral"])
        cadence: dict[str, object] | None = None
        if pn == "V" and cn in ("I", "i"):
            cadence = {
                "type": "authentic",
                "strength": "strong",
                "narrative": "resolution -- the harmony arrives home",
            }
        elif pn in ("IV", "iv") and cn in ("I", "i"):
            cadence = {
                "type": "plagal",
                "strength": "gentle",
                "narrative": "warm resolution -- the amen cadence",
            }
        elif cn == "V" and pn != "V":
            cadence = {
                "type": "half",
                "strength": "suspense",
                "narrative": "suspension -- the harmony pauses on tension",
            }
        elif pn == "V" and cn in ("vi", "VI"):
            cadence = {
                "type": "deceptive",
                "strength": "surprise",
                "narrative": "deception -- expected home, got shadow instead",
            }
        elif cn == "i" and pn in ("v", "VII", "V"):
            cadence = {
                "type": "minor_authentic",
                "strength": "dark",
                "narrative": "dark resolution -- home is minor",
            }
        if cadence:
            cadence["time"] = curr.get("start", 0)
            cadence["label"] = curr.get("label", "")
            cadence["from"] = pn
            cadence["to"] = cn
            cadences.append(cadence)
    return cadences


def analyze(chords: dict[str, object]) -> dict[str, object]:
    """Read key/mode, Roman numerals and cadences from the chord-progression dict.

    ``chords`` is chord_progression's output dict.
    """
    segments = chords.get("segments", [])
    if not isinstance(segments, list) or not segments:
        return cast("dict[str, object]", sanitize(_empty_result()))

    key_root, key_mode, key_confidence = _detect_key(segments)

    analyzed: list[dict[str, object]] = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        chord = str(seg.get("chord", ""))
        start = float(seg.get("start", 0))
        analysis = _chord_to_roman(chord, key_root, key_mode)
        analyzed.append(
            {
                "chord": chord,
                "start": start,
                "end": float(seg.get("end", 0)),
                "label": f"{int(start // 60)}:{int(start % 60):02d}",
                "analysis": analysis,
            }
        )

    cadences = _detect_cadences(analyzed)

    numerals_used: set[str] = set()
    for a in analyzed:
        if isinstance(a.get("analysis"), dict):
            numerals_used.add(str(cast("dict[str, object]", a["analysis"])["numeral"]))

    chromatic_count = sum(
        1
        for a in analyzed
        if isinstance(a.get("analysis"), dict)
        and bool(cast("dict[str, object]", a["analysis"]).get("is_chromatic"))
    )
    cadence_types: dict[str, int] = {}
    for c in cadences:
        t = str(c["type"])
        cadence_types[t] = cadence_types.get(t, 0) + 1

    result: dict[str, object] = {
        "key": key_root,
        "mode": key_mode,
        "key_confidence": key_confidence,
        "total_chords": len(segments),
        "unique_numerals": sorted(numerals_used),
        "harmonic_vocabulary_size": len(numerals_used),
        "chromatic_chords_pct": round(chromatic_count / max(len(segments), 1) * 100, 1),
        "total_cadences": len(cadences),
        "cadence_distribution": cadence_types,
        "cadences": cadences[:50],
        "analyzed_chords": analyzed[:200],
    }
    return cast("dict[str, object]", sanitize(result))
