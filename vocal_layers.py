#!/usr/bin/env python3
"""Claude's Ears - Vocal Layering Detection
Detects multiple simultaneous vocal lines, echoes, and harmonies in the vocal stem."""

import numpy as np, librosa, json, sys, warnings
warnings.filterwarnings('ignore')

def detect_vocal_layers(vocal_path, sr=22050):
    print("  Analyzing vocal layers...")
    y, sr = librosa.load(vocal_path, sr=sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)
    results = {"duration": round(duration, 2)}

    # Primary pitch
    f0, voiced, vprob = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C6'), sr=sr)
    voiced_mask = ~np.isnan(f0)

    # Spectral analysis in vocal band (200-4000 Hz)
    print("    Harmonic peak counting...")
    S = np.abs(librosa.stft(y, n_fft=2048))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    vm = (freqs >= 200) & (freqs <= 4000)
    vocal_S = S[vm, :]

    # Count spectral peaks per frame (more peaks = more voices)
    peak_counts = []
    for i in range(vocal_S.shape[1]):
        frame = vocal_S[:, i]
        if frame.max() > 0:
            threshold = frame.max() * 0.15
            peaks, in_peak = 0, False
            for val in frame:
                if val > threshold and not in_peak: peaks += 1; in_peak = True
                elif val < threshold: in_peak = False
            peak_counts.append(peaks)
        else:
            peak_counts.append(0)
    peak_counts = np.array(peak_counts)

    # Map peaks to voiced frames
    hop, f0_frames, pc_frames = 512, len(f0), len(peak_counts)
    ratio = pc_frames / max(f0_frames, 1)
    voiced_peaks = [peak_counts[int(i*ratio)] for i in range(f0_frames) if voiced_mask[i] and int(i*ratio) < pc_frames]

    avg_peaks = float(np.mean(voiced_peaks)) if voiced_peaks else 0
    p90_peaks = float(np.percentile(voiced_peaks, 90)) if voiced_peaks else 0
    results["harmonic_peaks_mean"] = round(avg_peaks, 1)
    results["harmonic_peaks_p90"] = round(p90_peaks, 1)

    if avg_peaks > 10: results["layering"] = "heavily layered (multiple voices)"
    elif avg_peaks > 7: results["layering"] = "doubled / harmonized"
    elif avg_peaks > 4: results["layering"] = "solo with occasional doubling"
    else: results["layering"] = "solo voice"

    # Echo detection via autocorrelation of RMS envelope
    print("    Echo detection...")
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    if len(rms) > 100:
        rms_norm = (rms - np.mean(rms)) / (np.std(rms) + 1e-10)
        autocorr = np.correlate(rms_norm, rms_norm, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        autocorr = autocorr / (autocorr[0] + 1e-10)
        min_lag, max_lag = 10, min(200, len(autocorr))
        search = autocorr[min_lag:max_lag]
        echo_peaks = []
        if len(search) > 10:
            for i in range(1, len(search)-1):
                if search[i] > search[i-1] and search[i] > search[i+1] and search[i] > 0.3:
                    echo_peaks.append({"delay_s": round((i+min_lag)*512/sr, 3), "strength": round(float(search[i]), 3)})
        results["echo_detected"] = len(echo_peaks) > 0
        results["echo_count"] = len(echo_peaks)
        results["echoes"] = echo_peaks[:5]
        results["echo_desc"] = f"{len(echo_peaks)} echo(es), primary {echo_peaks[0]['delay_s']:.2f}s" if echo_peaks else "no echo"
    else:
        results["echo_detected"] = False
        results["echo_desc"] = "insufficient data"

    # Find densest vocal regions (most layering)
    if len(peak_counts) > 0:
        ft = librosa.frames_to_time(range(len(peak_counts)), sr=sr, hop_length=512)
        high = np.percentile(peak_counts, 90)
        dense = peak_counts > high
        regions, in_r, start = [], False, 0
        for i in range(len(dense)):
            if dense[i] and not in_r: start = i; in_r = True
            elif not dense[i] and in_r:
                if i - start > 3:
                    regions.append({"start": round(float(ft[start]),2), "end": round(float(ft[min(i,len(ft)-1)]),2),
                                    "density": round(float(np.mean(peak_counts[start:i])),1)})
                in_r = False
        results["dense_regions"] = regions[:10]
        results["layering_pct"] = round(float(np.mean(dense))*100, 1)

    print(f"    Layering: {results['layering']}")
    print(f"    Echo: {results.get('echo_desc','?')}")
    print(f"    Layered sections: {len(results.get('dense_regions',[]))}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2: print("Usage: python vocal_layers.py <vocals.wav>"); sys.exit(1)
    r = detect_vocal_layers(sys.argv[1])
    out = sys.argv[1].rsplit('.',1)[0] + '_layers.json'
    with open(out,'w') as f: json.dump(r, f, indent=2)
    print(f"\nSaved: {out}")
    print(json.dumps(r, indent=2))
