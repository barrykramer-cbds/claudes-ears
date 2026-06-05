#!/usr/bin/env python3
"""Claude's Ears - Depth/Reverb Perception
Measures the Z-axis: how far away is the sound source?
RT60, pre-delay, wet/dry ratio, room size estimation."""

import numpy as np, librosa, json, sys, os, warnings
warnings.filterwarnings('ignore')

def estimate_reverb(file_path, sr=22050):
    """Estimate reverb characteristics from audio."""
    print(f"  Depth perception: {os.path.basename(file_path)}...")
    y, sr = librosa.load(file_path, sr=sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)
    results = {"duration": round(duration, 2)}

    # Method 1: Onset-to-decay analysis
    # Find sharp onsets and measure how long the energy takes to decay
    print("    Analyzing onset decay profiles...")
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    decay_times = []
    pre_delays = []
    hop = 512

    for onset_frame in onset_frames[:30]:  # sample up to 30 onsets
        start_sample = onset_frame * hop
        # Look at 2 seconds after onset
        window = y[start_sample:start_sample + sr * 2]
        if len(window) < sr:
            continue

        # Compute envelope
        envelope = np.abs(window)
        # Smooth
        kernel = np.ones(256) / 256
        if len(envelope) > 256:
            envelope_smooth = np.convolve(envelope, kernel, mode='same')
        else:
            continue

        peak_idx = np.argmax(envelope_smooth[:sr//2])  # peak within first 0.5s
        peak_val = envelope_smooth[peak_idx]

        if peak_val < 0.01:
            continue

        # Pre-delay: time from onset to peak
        pre_delay_sec = peak_idx / sr
        if 0.001 < pre_delay_sec < 0.1:
            pre_delays.append(pre_delay_sec)

        # RT60 estimate: time for energy to drop 60dB (or to 0.001 of peak)
        threshold = peak_val * 0.001  # -60dB
        decay_idx = None
        for i in range(peak_idx, len(envelope_smooth)):
            if envelope_smooth[i] < threshold:
                decay_idx = i
                break

        if decay_idx:
            rt60 = (decay_idx - peak_idx) / sr
            if 0.05 < rt60 < 5.0:  # reasonable reverb range
                decay_times.append(rt60)

    if decay_times:
        results["rt60_estimate"] = round(float(np.median(decay_times)), 4)
        results["rt60_std"] = round(float(np.std(decay_times)), 4)
    else:
        results["rt60_estimate"] = 0

    if pre_delays:
        results["pre_delay_ms"] = round(float(np.median(pre_delays)) * 1000, 2)
    else:
        results["pre_delay_ms"] = 0

    # Method 2: Spectral decay rate
    # Reverberant audio has slower spectral decay than dry audio
    print("    Spectral decay analysis...")
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))

    # Compute autocorrelation of spectral frames
    # High autocorrelation = more reverb (energy persists)
    spectral_persistence = []
    for band_start in range(0, S.shape[0], 20):
        band = S[band_start:band_start+20, :]
        band_energy = band.mean(axis=0)
        if len(band_energy) > 10 and np.std(band_energy) > 0:
            band_norm = (band_energy - np.mean(band_energy)) / (np.std(band_energy) + 1e-10)
            autocorr = np.correlate(band_norm[:500], band_norm[:500], mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            if len(autocorr) > 5 and autocorr[0] > 0:
                # Persistence = ratio of autocorrelation at lag 3 vs lag 0
                persistence = autocorr[3] / autocorr[0] if autocorr[0] > 0 else 0
                spectral_persistence.append(max(0, persistence))

    if spectral_persistence:
        results["spectral_persistence"] = round(float(np.mean(spectral_persistence)), 4)
    else:
        results["spectral_persistence"] = 0

    # Method 3: Wet/Dry estimation from spectral flatness variation
    # Reverb increases spectral flatness (smears the spectrum)
    flatness = librosa.feature.spectral_flatness(y=y)[0]
    results["spectral_flatness_mean"] = round(float(np.mean(flatness)), 4)
    results["spectral_flatness_std"] = round(float(np.std(flatness)), 4)

    # Wet/dry heuristic: higher flatness + higher persistence = more reverb
    wetness = (results.get("spectral_persistence", 0) * 0.5 +
               results.get("spectral_flatness_mean", 0) * 5.0 +
               min(results.get("rt60_estimate", 0), 2.0) * 0.3)
    results["wetness_index"] = round(float(min(wetness, 1.0)), 4)

    # Room size estimation from RT60
    rt60 = results.get("rt60_estimate", 0)
    if rt60 > 1.5:
        room = "cathedral / large hall"
        distance = "far - across the room"
    elif rt60 > 0.8:
        room = "concert hall / large studio"
        distance = "moderate - middle of room"
    elif rt60 > 0.4:
        room = "medium room / studio"
        distance = "near - close mic with room"
    elif rt60 > 0.15:
        room = "small room / vocal booth"
        distance = "intimate - close to ear"
    else:
        room = "dry / close-mic / no room"
        distance = "in your ear"

    results["room_size"] = room
    results["perceived_distance"] = distance

    # Pre-delay interpretation
    pd = results.get("pre_delay_ms", 0)
    if pd > 40:
        results["spatial_placement"] = "source is far from reflective surfaces"
    elif pd > 20:
        results["spatial_placement"] = "source is moderately placed in room"
    elif pd > 5:
        results["spatial_placement"] = "source is close to reflective surface"
    else:
        results["spatial_placement"] = "direct / no early reflections"

    print(f"\n  DEPTH PERCEPTION")
    print(f"  {'='*50}")
    print(f"  RT60 (reverb time): {results['rt60_estimate']:.3f}s")
    print(f"  Pre-delay: {results['pre_delay_ms']:.1f}ms")
    print(f"  Wetness: {results['wetness_index']:.3f}")
    print(f"  Room: {results['room_size']}")
    print(f"  Distance: {results['perceived_distance']}")
    print(f"  Spatial: {results['spatial_placement']}")
    print(f"  {'='*50}")

    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python depth_reverb.py <audio_file>")
        sys.exit(1)
    r = estimate_reverb(sys.argv[1])
    out = sys.argv[1].rsplit('.',1)[0] + '_depth.json'
    with open(out, 'w') as f:
        json.dump(r, f, indent=2)
    print(f"\nSaved: {out}")
