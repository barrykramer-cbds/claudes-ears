"""
Claude's Ears — Stem Analysis
Run locally: python analyze_stems.py <stems_directory>
Outputs JSON with per-stem perception data.
"""
import os, sys, json, warnings
warnings.filterwarnings('ignore')
import numpy as np
import librosa

def analyze_vocal(path):
    print("  Analyzing vocals...")
    y, sr = librosa.load(path, sr=22050, mono=True)
    results = {"stem": "vocals", "duration": round(librosa.get_duration(y=y, sr=sr), 2)}

    f0, voiced, vprob = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C6'), sr=sr)
    voiced_f0 = f0[~np.isnan(f0)]

    if len(voiced_f0) > 10:
        results["pitch_mean_hz"] = round(float(np.mean(voiced_f0)), 1)
        results["pitch_range_semitones"] = round(float(np.ptp(librosa.hz_to_midi(voiced_f0))), 1)
        results["voiced_fraction"] = round(float(np.mean(~np.isnan(f0))), 3)

        midi = np.round(librosa.hz_to_midi(voiced_f0)).astype(int)
        trans = np.zeros((12, 12))
        for i in range(len(midi)-1):
            trans[midi[i]%12, midi[i+1]%12] += 1
        rs = trans.sum(axis=1, keepdims=True); rs[rs==0] = 1
        tp = trans / rs
        ent = [float(-np.sum(r[r>0]*np.log2(r[r>0]))) for r in tp if (r>0).any()]
        results["vocal_melodic_entropy"] = round(float(np.mean(ent)), 4) if ent else 0

    flatness = librosa.feature.spectral_flatness(y=y)[0]
    results["breathiness"] = round(float(np.mean(flatness)), 4)
    results["breathiness_desc"] = "airy" if np.mean(flatness)>0.1 else "clear" if np.mean(flatness)>0.01 else "pure"

    rms = librosa.amplitude_to_db(librosa.feature.rms(y=y)[0], ref=np.max)
    good = rms[rms > -60]
    results["dynamic_range_db"] = round(float(np.ptp(good)), 1) if len(good) > 0 else 0
    return results

def analyze_drums(path):
    print("  Analyzing drums...")
    y, sr = librosa.load(path, sr=22050, mono=True)
    results = {"stem": "drums", "duration": round(librosa.get_duration(y=y, sr=sr), 2)}

    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    results["tempo_bpm"] = round(float(np.atleast_1d(tempo)[0]), 1)
    bt = librosa.frames_to_time(beats, sr=sr)
    if len(bt) > 2:
        intervals = np.diff(bt)
        results["beat_regularity"] = round(1.0 - (np.std(intervals)/np.mean(intervals)), 4)

    onsets = librosa.onset.onset_detect(y=y, sr=sr)
    ot = librosa.frames_to_time(onsets, sr=sr)
    dur = librosa.get_duration(y=y, sr=sr)
    results["onsets_per_second"] = round(len(ot)/max(dur,1), 2)

    S = np.abs(librosa.stft(y)); freqs = librosa.fft_frequencies(sr=sr)
    kick = float(np.mean(S[(freqs>=20)&(freqs<=150),:])) if ((freqs>=20)&(freqs<=150)).any() else 0
    snare = float(np.mean(S[(freqs>=150)&(freqs<=1000),:])) if ((freqs>=150)&(freqs<=1000)).any() else 0
    hat = float(np.mean(S[freqs>=5000,:])) if (freqs>=5000).any() else 0
    total = kick+snare+hat+1e-10
    results["kit_balance"] = {"kick": round(kick/total*100,1), "snare": round(snare/total*100,1), "hihat": round(hat/total*100,1)}
    return results

def analyze_bass(path):
    print("  Analyzing bass...")
    y, sr = librosa.load(path, sr=22050, mono=True)
    results = {"stem": "bass", "duration": round(librosa.get_duration(y=y, sr=sr), 2)}

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    cm = chroma.mean(axis=1)
    pcs = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    results["dominant_notes"] = [pcs[i] for i in np.argsort(cm)[::-1][:4]]

    dom = np.argmax(chroma, axis=0)
    changes = np.sum(np.diff(dom)!=0)
    rate = changes/max(len(dom),1)
    results["root_movement_rate"] = round(rate, 4)
    results["root_movement_desc"] = "highly active" if rate>0.3 else "moderate" if rate>0.15 else "anchored"
    return results

def analyze_other(path):
    print("  Analyzing other (guitars/synths/keys)...")
    y, sr = librosa.load(path, sr=22050, mono=True)
    results = {"stem": "other", "duration": round(librosa.get_duration(y=y, sr=sr), 2)}

    centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))
    bw = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]))
    flat = float(np.mean(librosa.feature.spectral_flatness(y=y)[0]))
    results["centroid_hz"] = round(centroid, 1)
    results["bandwidth_hz"] = round(bw, 1)

    if flat > 0.1: tex = "noisy / distorted"
    elif centroid > 4000: tex = "bright / shimmering"
    elif centroid < 1500: tex = "dark / warm pads"
    elif bw > 3000: tex = "wide / full"
    else: tex = "focused / midrange"
    results["texture"] = tex

    yh, yp = librosa.effects.hpss(y)
    he, pe = float(np.sum(yh**2)), float(np.sum(yp**2))
    t = he+pe+1e-10
    results["harmonic_pct"] = round(he/t*100, 1)

    oe = librosa.onset.onset_strength(y=y, sr=sr)
    results["attack"] = "rhythmic" if np.std(oe)>3 else "moderate" if np.std(oe)>1.5 else "sustained / pad-like"
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_stems.py <stems_directory>")
        return

    stems_dir = sys.argv[1]
    results = {}

    for name in ["vocals", "drums", "bass", "other"]:
        for ext in [".wav", ".mp3"]:
            p = os.path.join(stems_dir, name+ext)
            if os.path.exists(p):
                if name == "vocals": results[name] = analyze_vocal(p)
                elif name == "drums": results[name] = analyze_drums(p)
                elif name == "bass": results[name] = analyze_bass(p)
                else: results[name] = analyze_other(p)
                break

    out = os.path.join(stems_dir, "stem_analysis.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print("STEM ANALYSIS COMPLETE")
    print(f"{'='*60}")
    for stem, data in results.items():
        print(f"\n  {stem.upper()}:")
        for k, v in data.items():
            if k != "stem":
                print(f"    {k}: {v}")
    print(f"\nSaved: {out}")

if __name__ == "__main__":
    main()
