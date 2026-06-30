"""Rolling-window temporal analysis — snapshots and structural arc of the source mix."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import librosa
import numpy as np
import numpy.typing as npt

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from pathlib import Path

_SAMPLE_RATE = 22050
_WINDOW_SEC = 15
_HOP_SEC = 5

_PITCH_CLASSES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

# Interval consonance weights for tension computation
_CONS_W: dict[int, float] = {
    0: 1.0,
    7: 0.9,
    5: 0.85,
    4: 0.8,
    3: 0.75,
    8: 0.7,
    9: 0.7,
    2: 0.5,
    10: 0.5,
    6: 0.3,
    1: 0.2,
    11: 0.2,
}


def _snapshot(
    seg: npt.NDArray[np.float64],
    idx: int,
    pos: int,
    sr: int,
    window_sec: int,
) -> dict[str, object]:
    ws = window_sec * sr
    tc = (pos / sr + (pos + ws) / sr) / 2
    snap: dict[str, object] = {
        "seg": idx,
        "t_start": round(pos / sr, 2),
        "t_end": round((pos + ws) / sr, 2),
        "t_center": round(tc, 2),
        "time": f"{int(tc // 60)}:{int(tc % 60):02d}",
    }

    rms = librosa.feature.rms(y=seg)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=float(np.max(rms)) if rms.size > 0 else 1.0)
    snap["rms_mean"] = round(float(np.mean(rms_db)), 2)
    snap["rms_p90"] = round(float(np.percentile(rms_db, 90)), 2)
    good = rms_db[rms_db > -60]
    snap["dyn_range"] = round(float(np.ptp(good)), 2) if len(good) > 1 else 0.0

    snap["centroid"] = round(float(np.mean(librosa.feature.spectral_centroid(y=seg, sr=sr)[0])), 1)

    yh, yp = librosa.effects.hpss(seg)
    he, pe = float(np.sum(yh**2)), float(np.sum(yp**2))
    snap["harm_pct"] = round(he / (he + pe + 1e-10) * 100, 1)

    chroma = librosa.feature.chroma_cqt(y=seg, sr=sr)
    cm = chroma.mean(axis=1)
    snap["key"] = _PITCH_CLASSES[int(np.argmax(cm))]

    cdists: list[float] = []
    for i in range(1, chroma.shape[1]):
        a, b = chroma[:, i - 1], chroma[:, i]
        na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
        if na > 0 and nb > 0:
            cdists.append(1 - float(np.dot(a, b)) / (na * nb))
    snap["tension"] = round(float(np.mean(cdists)), 4) if cdists else 0.0

    cscores: list[float] = []
    for i in range(chroma.shape[1]):
        fr = chroma[:, i]
        if fr.max() > 0:
            fr = fr / fr.max()
            s, tw = 0.0, 0.0
            for j in range(12):
                for k in range(j + 1, 12):
                    iv = (k - j) % 12
                    w = _CONS_W.get(iv, 0.5)
                    s += w * float(fr[j]) * float(fr[k])
                    tw += float(fr[j]) * float(fr[k])
            if tw > 0:
                cscores.append(s / tw)
    snap["consonance"] = round(float(np.mean(cscores)), 4) if cscores else 0.0

    spec = np.abs(librosa.stft(seg))
    freqs = librosa.fft_frequencies(sr=sr)
    wm = (freqs >= 200) & (freqs <= 2000)
    we = float(np.mean(spec[wm, :])) if wm.any() else 0.0
    snap["warmth"] = round(we / (float(np.mean(spec)) + 1e-10), 4)

    ons = librosa.onset.onset_detect(y=seg, sr=sr)
    snap["onset_density"] = round(len(ons) / window_sec, 2)

    tempo, _ = librosa.beat.beat_track(y=seg, sr=sr)
    snap["tempo"] = round(float(np.atleast_1d(tempo)[0]), 1)

    return snap


def _narrative(snaps: list[dict[str, object]]) -> dict[str, object]:
    """Summarize structural arc; returns {} when there are too few windows."""
    if not snaps:
        return {}

    n: dict[str, object] = {}

    rms_vals = [cast("float", s["rms_p90"]) for s in snaps]
    tension_vals = [cast("float", s["tension"]) for s in snaps]

    climax_snap = max(snaps, key=lambda s: cast("float", s["rms_p90"]))
    quietest_snap = min(snaps, key=lambda s: cast("float", s["rms_mean"]))
    tension_snap = max(snaps, key=lambda s: cast("float", s["tension"]))

    n["climax"] = {"time": climax_snap["time"], "db": climax_snap["rms_p90"]}
    n["quietest"] = {"time": quietest_snap["time"], "db": quietest_snap["rms_mean"]}
    n["peak_tension"] = {"time": tension_snap["time"], "val": tension_snap["tension"]}

    trans: list[dict[str, object]] = []
    for i in range(1, len(rms_vals)):
        d = rms_vals[i] - rms_vals[i - 1]
        if abs(d) > 3:
            trans.append(
                {
                    "time": snaps[i]["time"],
                    "type": "BUILD" if d > 0 else "DROP",
                    "db": round(d, 1),
                }
            )
    n["transitions"] = trans

    kc: list[dict[str, object]] = []
    for i in range(1, len(snaps)):
        if snaps[i]["key"] != snaps[i - 1]["key"]:
            kc.append(
                {"time": snaps[i]["time"], "from": snaps[i - 1]["key"], "to": snaps[i]["key"]}
            )
    n["key_changes"] = kc

    # guard zero-length thirds — fewer than 3 snapshots makes the arc undefined
    count = len(snaps)
    if count >= 3:
        t = count // 3
        e1 = float(np.mean(rms_vals[:t]))
        e2 = float(np.mean(rms_vals[t : 2 * t]))
        e3 = float(np.mean(rms_vals[2 * t :]))
        t1 = float(np.mean(tension_vals[:t]))
        t2 = float(np.mean(tension_vals[t : 2 * t]))
        t3 = float(np.mean(tension_vals[2 * t :]))

        if e2 > e1 and e2 > e3:
            earc = "peak in middle"
        elif e3 > e2 > e1:
            earc = "continuous build"
        elif e1 > e2 > e3:
            earc = "continuous decay"
        else:
            earc = "complex"

        n["arc"] = {
            "energy": earc,
            "e_thirds": [round(e1, 1), round(e2, 1), round(e3, 1)],
            "t_thirds": [round(t1, 4), round(t2, 4), round(t3, 4)],
        }

    return n


def analyze(audio: Path) -> dict[str, object]:
    """Snapshot the source mix over time and summarize its structural arc."""
    y, sr_raw = librosa.load(str(audio), sr=_SAMPLE_RATE, mono=True)
    sr = int(sr_raw)

    ws = _WINDOW_SEC * sr
    hs = _HOP_SEC * sr
    snapshots: list[dict[str, object]] = []
    pos, idx = 0, 0

    while pos + ws <= len(y):
        snapshots.append(_snapshot(y[pos : pos + ws], idx, pos, sr, _WINDOW_SEC))
        pos += hs
        idx += 1

    result: dict[str, object] = {
        "snapshots": snapshots,
        "narrative": _narrative(snapshots),
    }
    return cast("dict[str, object]", sanitize(result))
