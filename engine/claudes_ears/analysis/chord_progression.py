"""Per-beat chord identification and harmonic-journey tracking from the source mix."""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, cast

import librosa
import numpy as np
import numpy.typing as npt

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path

_PITCH_CLASSES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

_CHORD_INTERVALS: dict[str, tuple[int, ...]] = {
    "": (0, 4, 7),
    "m": (0, 3, 7),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "7": (0, 4, 7, 10),
    "m7": (0, 3, 7, 10),
    "maj7": (0, 4, 7, 11),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
}

_NO_CHORD = "N.C."
_SAMPLE_RATE = 22050
_MODULATION_WINDOW_BEATS = 8


def _build_templates() -> dict[str, npt.NDArray[np.float64]]:
    """Build unit-norm 12-dim chroma templates for every root/quality pair."""
    templates: dict[str, npt.NDArray[np.float64]] = {}
    for root_idx, root in enumerate(_PITCH_CLASSES):
        for suffix, intervals in _CHORD_INTERVALS.items():
            template = np.zeros(12, dtype=np.float64)
            for interval in intervals:
                template[(root_idx + interval) % 12] = 1.0
            template /= np.linalg.norm(template)
            templates[f"{root}{suffix}"] = template
    return templates


_TEMPLATES = _build_templates()


def _identify_chord(chroma_frame: npt.NDArray[np.float64]) -> tuple[str, float]:
    """Match one chroma frame to its best chord template; silence -> no-chord."""
    norm = float(np.linalg.norm(chroma_frame))
    if norm < 0.01:
        return _NO_CHORD, 0.0
    frame = chroma_frame / norm
    best_name, best_score = _NO_CHORD, 0.0
    for name, template in _TEMPLATES.items():
        score = float(np.dot(frame, template))
        if score > best_score:
            best_name, best_score = name, score
    return best_name, round(best_score, 4)


def _empty_result(tempo: float = 0.0) -> dict[str, object]:
    """Degraded contract for silent/too-short audio: required keys, empty lists."""
    return {
        "tempo": tempo,
        "total_beats": 0,
        "total_segments": 0,
        "unique_chords": 0,
        "segments": [],
        "top_patterns": [],
        "modulations": [],
        "chord_sequence_summary": [],
    }


def _segments_from_beats(
    beat_chords: list[dict[str, object]], duration: float, total_beats: int
) -> list[dict[str, object]]:
    """Merge consecutive equal-chord beats into duration-bearing segments."""
    if not beat_chords:
        return []
    segments: list[dict[str, object]] = []
    first = beat_chords[0]
    chord = str(first["chord"])
    start = float(cast("float", first["time"]))
    start_beat = 1
    confidences = [float(cast("float", first["confidence"]))]
    for entry in beat_chords[1:]:
        entry_chord = str(entry["chord"])
        if entry_chord == chord:
            confidences.append(float(cast("float", entry["confidence"])))
            continue
        end_beat = int(cast("int", entry["beat"])) - 1
        segments.append(
            {
                "chord": chord,
                "start": start,
                "start_beat": start_beat,
                "end": float(cast("float", entry["time"])),
                "end_beat": end_beat,
                "duration_beats": end_beat - start_beat + 1,
                "avg_confidence": round(float(np.mean(confidences)), 4),
            }
        )
        chord = entry_chord
        start = float(cast("float", entry["time"]))
        start_beat = int(cast("int", entry["beat"]))
        confidences = [float(cast("float", entry["confidence"]))]
    segments.append(
        {
            "chord": chord,
            "start": start,
            "start_beat": start_beat,
            "end": round(duration, 3),
            "end_beat": total_beats,
            "duration_beats": total_beats - start_beat + 1,
            "avg_confidence": round(float(np.mean(confidences)), 4),
        }
    )
    return segments


def _top_patterns(chord_sequence: list[str]) -> list[dict[str, object]]:
    """Rank recurring 4-chord sequences by frequency, top 10."""
    counts: dict[str, int] = {}
    for i in range(len(chord_sequence) - 3):
        pattern = " -> ".join(chord_sequence[i : i + 4])
        counts[pattern] = counts.get(pattern, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: -item[1])[:10]
    return [{"pattern": pattern, "count": count} for pattern, count in ranked]


def _modulations(
    chroma: npt.NDArray[np.float64],
    beat_frames: npt.NDArray[np.intp],
    beat_times: npt.NDArray[np.float64],
) -> list[dict[str, object]]:
    """Detect key-center shifts across half-overlapping 8-beat windows, capped at 20."""
    window = _MODULATION_WINDOW_BEATS
    centers: list[dict[str, object]] = []
    last_index = len(beat_frames) - 1
    for i in range(0, last_index - window, window // 2):
        end_idx = int(beat_frames[min(i + window, last_index)])
        window_chroma = chroma[:, int(beat_frames[i]) : end_idx].mean(axis=1)
        centers.append(
            {
                "time": round(float(beat_times[i]), 2),
                "center": _PITCH_CLASSES[int(np.argmax(window_chroma))],
            }
        )
    shifts: list[dict[str, object]] = []
    for prev, current in pairwise(centers):
        if current["center"] != prev["center"]:
            shifts.append(
                {"time": current["time"], "from": prev["center"], "to": current["center"]}
            )
    return shifts[:20]


def analyze(audio: Path) -> dict[str, object]:
    """Detect chord segments and tempo from the source mix.

    Emits ``segments[]`` and ``tempo`` consumed downstream by music_theory/harmonic_rhythm.
    """
    y, sr = librosa.load(str(audio), sr=_SAMPLE_RATE, mono=True)
    if y.size == 0:
        return cast("dict[str, object]", sanitize(_empty_result()))

    duration = float(librosa.get_duration(y=y, sr=sr))
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).astype(np.float64)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = round(float(np.atleast_1d(tempo)[0]), 1)
    if beat_frames.size == 0:
        return cast("dict[str, object]", sanitize(_empty_result(tempo_val)))

    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    beat_chords: list[dict[str, object]] = []
    for i, frame in enumerate(beat_frames):
        end = int(beat_frames[i + 1]) if i + 1 < len(beat_frames) else chroma.shape[1]
        avg_chroma = chroma[:, int(frame) : end].mean(axis=1)
        chord, confidence = _identify_chord(avg_chroma)
        beat_chords.append(
            {
                "beat": i + 1,
                "time": round(float(beat_times[i]), 3),
                "chord": chord,
                "confidence": confidence,
            }
        )

    segments = _segments_from_beats(beat_chords, duration, len(beat_chords))
    chord_sequence = [str(s["chord"]) for s in segments if s["chord"] != _NO_CHORD]
    result = {
        "tempo": tempo_val,
        "total_beats": len(beat_chords),
        "total_segments": len(segments),
        "unique_chords": len({str(s["chord"]) for s in segments}),
        "segments": segments,
        "top_patterns": _top_patterns(chord_sequence),
        "modulations": _modulations(chroma, beat_frames, beat_times),
        "chord_sequence_summary": chord_sequence[:50],
    }
    return cast("dict[str, object]", sanitize(result))
