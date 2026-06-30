"""Vocal relationship taxonomy over time (schema §5 variant shapes).

Labels each window solo|support|dialogue|opposition|merge|withdraw|silence;
silence/instrumental frames drop the per-register percentages (-> None).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import librosa
import numpy as np
import numpy.typing as npt
from scipy.ndimage import label as connected_components

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path

_SR = 22050
_WINDOW_SEC = 2.0
_HOP = 512
_N_FFT = 2048
_MIN_PITCH_HZ = 80.0
_SILENCE_RMS = 0.003

_Moment = dict[str, object]


def _lead_baseline(y: npt.NDArray[np.float64], sr: int) -> tuple[float, float, float]:
    """Lead voice as median dominant pitch and its IQR; defaults if pitch-less."""
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr, n_fft=_N_FFT, hop_length=_HOP)
    dominant: list[float] = []
    for frame in range(pitches.shape[1]):
        idx = int(magnitudes[:, frame].argmax())
        pitch = float(pitches[idx, frame])
        if pitch > _MIN_PITCH_HZ:
            dominant.append(pitch)
    if not dominant:
        return 300.0, 200.0, 400.0
    return (
        float(np.median(dominant)),
        float(np.percentile(dominant, 25)),
        float(np.percentile(dominant, 75)),
    )


def _register_energy(
    seg: npt.NDArray[np.float64], sr: int, lead_low: float, lead_high: float
) -> tuple[list[float], float, float, float]:
    """Sum strong-pitch magnitude into lead/below/above register bands."""
    seg_pitches, seg_mags = librosa.piptrack(y=seg, sr=sr, n_fft=_N_FFT, hop_length=_HOP)
    active: list[float] = []
    lead_e = below_e = above_e = 0.0
    for frame in range(seg_pitches.shape[1]):
        frame_p = seg_pitches[:, frame]
        frame_m = seg_mags[:, frame]
        positive = frame_m[frame_m > 0]
        threshold = float(np.percentile(positive, 30)) if positive.size else 0.0
        for idx in range(len(frame_p)):
            pitch = float(frame_p[idx])
            mag = float(frame_m[idx])
            if pitch > _MIN_PITCH_HZ and mag > threshold:
                active.append(pitch)
                if lead_low * 0.8 <= pitch <= lead_high * 1.2:
                    lead_e += mag
                elif pitch < lead_low * 0.8:
                    below_e += mag
                else:
                    above_e += mag
    return active, lead_e, below_e, above_e


def _pitch_density(active: list[float]) -> int:
    """Distinct pitch clusters in the window — the relationship's voice count."""
    hist, _ = np.histogram(active, bins=48, range=(80, 1200))
    smoothed = np.convolve(hist, np.ones(3) / 3, mode="same")
    peak = float(np.max(smoothed))
    binary = (smoothed > peak * 0.15).astype(int)
    _, clusters = connected_components(binary)
    return int(clusters)


def _classify(
    density: int,
    density_change: int,
    lead_present: bool,
    support_register: str,
    prev_relationship: str,
) -> tuple[str, str]:
    """Map window features to a (relationship, narrative) per the taxonomy."""
    withdrawing = prev_relationship in ("support", "merge", "dialogue", "opposition")
    if density <= 1 and lead_present:
        if withdrawing and density_change < 0:
            return "withdraw", "the arrangement opens a spotlight for the lead voice"
        return "solo", "vocal spotlight  -- one voice expressing the lyric unaccompanied"

    if density >= 3 and lead_present:
        if support_register == "below":
            return "support", "voices lifting from below, the ground holding the sky"
        if support_register == "above":
            return "support", "voices shimmering above, adding light"
        if support_register == "both":
            return "merge", "voices surrounding, becoming one sound"
        return "support", "voices gathering to carry the lead higher"

    if density == 2 and lead_present:
        if density_change > 0:
            if support_register == "below":
                return "support", "a second voice enters below, offering foundation"
            if support_register == "above":
                return "dialogue", "a voice answers from above"
            return "dialogue", "two voices in conversation"
        if density_change < 0:
            return "withdraw", "voices stepping back, spotlight narrowing to the lead"
        if support_register in ("below", "both"):
            return "support", "held in harmony, the lead supported"
        return "dialogue", "voices trading space"

    if not lead_present and density >= 2:
        return "opposition", "voices without a clear lead, collective speech"

    if density_change < -1:
        return "withdraw", "the arrangement clears the stage for the solo voice"

    return "solo", "vocal spotlight  -- the performer given the stage to express"


def _label(t: float) -> str:
    """Format a time in seconds as M:SS."""
    return f"{int(t // 60)}:{int(t % 60):02d}"


def _silence_moment(t: float, energy_db: float, narrative: str) -> _Moment:
    """A frame with no lead — drops the per-register percentages (schema §5 variant)."""
    return {
        "time": round(t, 2),
        "label": _label(t),
        "relationship": "silence",
        "energy_db": energy_db,
        "density": 0,
        "density_change": 0,
        "lead_present": False,
        "support_register": "none",
        "narrative": narrative,
    }


def _build_story(moments: list[_Moment]) -> list[_Moment]:
    """Merge consecutive same-relationship moments into story phases."""
    if not moments:
        return []
    story: list[_Moment] = []

    def begin(m: _Moment) -> tuple[_Moment, list[_Moment]]:
        return {
            "relationship": m["relationship"],
            "narrative": m["narrative"],
            "start": m["label"],
            "start_time": m["time"],
        }, [m]

    def close(phase: _Moment, frames: list[_Moment], end: _Moment) -> None:
        start_time = float(phase["start_time"])  # type: ignore[arg-type]
        densities = [float(f["density"]) for f in frames]  # type: ignore[arg-type]
        phase["end"] = end["label"]
        phase["duration_s"] = round(float(end["time"]) - start_time, 1)  # type: ignore[arg-type]
        phase["avg_density"] = round(float(np.mean(densities)), 1)
        story.append(phase)

    current, frames = begin(moments[0])
    for m in moments[1:]:
        if m["relationship"] == current["relationship"]:
            frames.append(m)
        else:
            close(current, frames, m)
            current, frames = begin(m)
    close(current, frames, moments[-1])
    return story


def _distribution(moments: list[_Moment]) -> dict[str, float]:
    """Percentage share of each relationship label across all moments."""
    total = len(moments)
    if not total:
        return {}
    counts: dict[str, int] = {}
    for m in moments:
        rel = str(m["relationship"])
        counts[rel] = counts.get(rel, 0) + 1
    return {rel: round(count / total * 100, 1) for rel, count in counts.items()}


def analyze(audio: Path, *, sr: int = _SR, window_sec: float = _WINDOW_SEC) -> dict[str, object]:
    """Label moment-to-moment vocal relationships (solo..withdraw) in the vocals stem."""
    y, _ = librosa.load(str(audio), sr=sr, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))

    ws = int(window_sec * sr)
    hs = int(window_sec * sr / 2)
    lead_center, lead_low, lead_high = _lead_baseline(y, sr)

    moments: list[_Moment] = []
    prev_density = 0
    prev_relationship = "silence"

    pos = 0
    while pos + ws <= len(y):
        seg = y[pos : pos + ws]
        t_center = (pos + ws / 2) / sr
        rms = float(np.sqrt(np.mean(seg**2)))

        if rms < _SILENCE_RMS:
            moments.append(_silence_moment(t_center, -60.0, "silence"))
            prev_density, prev_relationship = 0, "silence"
            pos += hs
            continue

        energy_db = round(float(20 * np.log10(rms + 1e-10)), 2)
        active, lead_e, below_e, above_e = _register_energy(seg, sr, lead_low, lead_high)

        if not active:
            moments.append(_silence_moment(t_center, energy_db, "instrumental"))
            prev_density, prev_relationship = 0, "silence"
            pos += hs
            continue

        density = _pitch_density(active)
        density_change = density - prev_density

        total = lead_e + below_e + above_e + 1e-10
        lead_pct = lead_e / total
        below_pct = below_e / total
        above_pct = above_e / total
        lead_present = lead_pct > 0.2

        if below_pct > 0.15 and above_pct > 0.15:
            support_register = "both"
        elif below_pct > 0.15:
            support_register = "below"
        elif above_pct > 0.15:
            support_register = "above"
        else:
            support_register = "none"

        relationship, narrative = _classify(
            density, density_change, lead_present, support_register, prev_relationship
        )

        moments.append(
            {
                "time": round(t_center, 2),
                "label": _label(t_center),
                "relationship": relationship,
                "energy_db": energy_db,
                "density": density,
                "density_change": density_change,
                "lead_present": lead_present,
                "lead_pct": round(lead_pct * 100, 1),
                "below_pct": round(below_pct * 100, 1),
                "above_pct": round(above_pct * 100, 1),
                "support_register": support_register,
                "narrative": narrative,
            }
        )
        prev_density, prev_relationship = density, relationship
        pos += hs

    story = _build_story(moments)
    transitions: list[_Moment] = [
        {
            "time": story[i + 1]["start"],
            "from": story[i]["relationship"],
            "to": story[i + 1]["relationship"],
            "from_narrative": story[i]["narrative"],
            "to_narrative": story[i + 1]["narrative"],
        }
        for i in range(len(story) - 1)
    ]

    results: dict[str, object] = {
        "duration": round(duration, 2),
        "lead_pitch_center": round(lead_center, 1),
        "total_story_phases": len(story),
        "total_transitions": len(transitions),
        "relationship_distribution": _distribution(moments),
        "story": story,
        "transitions": transitions[:30],
        "moments": moments,
    }
    return sanitize(results)  # type: ignore[return-value]
