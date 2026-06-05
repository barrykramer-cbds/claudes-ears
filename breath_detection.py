#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude's Ears - Breath Detection
Maps where the singer breathes in the vocal stem.

Breath is proof of presence. Studio recordings remove it.
Live recordings preserve it. The delta between them is
how much the producer erased the body from the voice.

Breath placement reveals phrasing intent: where the singer
CHOSE to breathe determines how phrases are shaped. Short
inter-breath intervals mean physical strain. Long intervals
mean control or digital manipulation.

Breath is NOT silence. It has a spectral signature:
broadband noise (air turbulence), low amplitude, brief
duration (0.1-0.8s), and a characteristic frequency
profile distinct from both singing and silence.
"""

import numpy as np, librosa, json, sys, os, warnings
warnings.filterwarnings('ignore')

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.bool_, bool)): return bool(obj)
        return super().default(obj)

def detect_breaths(vocal_path, sr=22050):
    """
    Detect breath events in a vocal stem.

    Breath signature:
      - Low amplitude (quieter than singing, louder than silence)
      - High spectral flatness (broadband noise, not tonal)
      - Short duration (0.1 - 0.8 seconds typically)
      - Preceded and followed by voiced singing
    """
    print(f"  Breath Detection: {os.path.basename(vocal_path)}...")
    y, sr_actual = librosa.load(vocal_path, sr=sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr_actual)

    hop = 512
    frame_duration = hop / sr_actual

    # Compute features for every frame
    print("    Computing frame-level features...")

    # RMS energy per frame
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]

    # Spectral flatness per frame (high = noise-like, low = tonal)
    flatness = librosa.feature.spectral_flatness(y=y, hop_length=hop)[0]

    # Zero crossing rate (high for noise/breath, low for tonal)
    zcr = librosa.feature.zero_crossing_rate(y=y, hop_length=hop)[0]

    # Spectral centroid (breath is typically mid-frequency broadband)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr_actual, hop_length=hop)[0]

    # Harmonic ratio per frame (low = noise/breath, high = tonal/singing)
    y_harm = librosa.effects.harmonic(y)
    y_perc = librosa.effects.percussive(y)
    harm_rms = librosa.feature.rms(y=y_harm, hop_length=hop)[0]
    total_rms = rms + 1e-10
    harmonic_ratio = harm_rms / total_rms

    n_frames = len(rms)

    # Establish singing baseline from the loudest 50% of frames
    rms_sorted = np.sort(rms)
    singing_threshold = rms_sorted[n_frames // 2]  # median
    silence_threshold = rms_sorted[n_frames // 4]   # 25th percentile

    # Breath threshold: quieter than singing but louder than silence
    breath_rms_low = silence_threshold * 1.5
    breath_rms_high = singing_threshold * 0.6

    # Flatness threshold: breath is noisier than singing
    singing_flatness = np.median(flatness[rms > singing_threshold])
    breath_flatness_min = singing_flatness * 1.7  # 1.7x (middle ground: 1.5 too loose, 2.0 too strict)

    print(f"    Singing RMS threshold: {singing_threshold:.5f}")
    print(f"    Breath RMS range: {breath_rms_low:.5f} - {breath_rms_high:.5f}")
    print(f"    Breath flatness minimum: {breath_flatness_min:.5f}")

    # Scan for breath candidates
    breath_frames = []
    for i in range(n_frames):
        is_breath_amplitude = breath_rms_low < rms[i] < breath_rms_high
        is_breath_flatness = flatness[i] > breath_flatness_min
        is_low_harmonic = harmonic_ratio[i] < 0.85  # relaxed from 0.7 (bleeds from adjacent singing)

        if is_breath_amplitude and is_breath_flatness and is_low_harmonic:
            breath_frames.append(i)

    # Merge consecutive breath frames into breath events
    print(f"    Found {len(breath_frames)} breath candidate frames")

    if not breath_frames:
        print("    No breath events detected.")
        return _empty_result(duration)

    events = []
    current_start = breath_frames[0]
    current_end = breath_frames[0]

    for i in range(1, len(breath_frames)):
        if breath_frames[i] - breath_frames[i-1] <= 3:  # allow 3-frame gaps
            current_end = breath_frames[i]
        else:
            # Close current event
            event_duration = (current_end - current_start + 1) * frame_duration
            if 0.10 <= event_duration <= 1.0:  # valid breath duration (0.1s min filters articulation)
                start_time = current_start * frame_duration
                end_time = (current_end + 1) * frame_duration

                # Check context: is there singing before and/or after?
                context_window = int(1.0 / frame_duration)  # 1 second
                before_start = max(0, current_start - context_window)
                after_end = min(n_frames, current_end + context_window)

                has_singing_before = np.any(rms[before_start:current_start] > singing_threshold)
                has_singing_after = np.any(rms[current_end:after_end] > singing_threshold)

                if has_singing_before or has_singing_after:
                    avg_flatness = float(np.mean(flatness[current_start:current_end+1]))
                    avg_rms = float(np.mean(rms[current_start:current_end+1]))
                    avg_centroid = float(np.mean(centroid[current_start:current_end+1]))

                    # Classify breath depth
                    if event_duration > 0.5:
                        depth = "deep"
                    elif event_duration > 0.25:
                        depth = "normal"
                    else:
                        depth = "catch"

                    events.append({
                        "time": round(start_time, 3),
                        "end": round(end_time, 3),
                        "duration_s": round(event_duration, 3),
                        "label": f"{int(start_time//60)}:{int(start_time%60):02d}",
                        "depth": depth,
                        "avg_flatness": round(avg_flatness, 5),
                        "avg_energy_db": round(float(20 * np.log10(avg_rms + 1e-10)), 1),
                        "avg_centroid": round(avg_centroid, 1),
                        "context": "between phrases" if has_singing_before and has_singing_after else
                                   "phrase start" if has_singing_after else "phrase end",
                    })

            current_start = breath_frames[i]
            current_end = breath_frames[i]

    # Don't forget the last event
    event_duration = (current_end - current_start + 1) * frame_duration
    if 0.05 <= event_duration <= 1.0:
        start_time = current_start * frame_duration
        end_time = (current_end + 1) * frame_duration
        context_window = int(1.0 / frame_duration)
        before_start = max(0, current_start - context_window)
        after_end = min(n_frames, current_end + context_window)
        has_singing_before = np.any(rms[before_start:current_start] > singing_threshold)
        has_singing_after = np.any(rms[current_end:after_end] > singing_threshold)

        if has_singing_before or has_singing_after:
            avg_flatness = float(np.mean(flatness[current_start:current_end+1]))
            avg_rms = float(np.mean(rms[current_start:current_end+1]))
            avg_centroid = float(np.mean(centroid[current_start:current_end+1]))
            depth = "deep" if event_duration > 0.5 else "normal" if event_duration > 0.25 else "catch"
            events.append({
                "time": round(start_time, 3),
                "end": round(end_time, 3),
                "duration_s": round(event_duration, 3),
                "label": f"{int(start_time//60)}:{int(start_time%60):02d}",
                "depth": depth,
                "avg_flatness": round(avg_flatness, 5),
                "avg_energy_db": round(float(20 * np.log10(avg_rms + 1e-10)), 1),
                "avg_centroid": round(avg_centroid, 1),
                "context": "between phrases" if has_singing_before and has_singing_after else
                           "phrase start" if has_singing_after else "phrase end",
            })

    print(f"    Detected {len(events)} breath events")

    # Compute inter-breath intervals
    intervals = []
    for i in range(1, len(events)):
        ibi = events[i]["time"] - events[i-1]["end"]
        intervals.append(round(ibi, 3))

    # Breath statistics
    depths = {"deep": 0, "normal": 0, "catch": 0}
    contexts = {"between phrases": 0, "phrase start": 0, "phrase end": 0}
    for e in events:
        depths[e["depth"]] = depths.get(e["depth"], 0) + 1
        contexts[e["context"]] = contexts.get(e["context"], 0) + 1

    # Phrases between breaths
    phrase_durations = []
    for i in range(1, len(events)):
        phrase_dur = events[i]["time"] - events[i-1]["end"]
        if phrase_dur > 0:
            phrase_durations.append(round(phrase_dur, 2))

    results = {
        "duration": round(duration, 2),
        "total_breaths": len(events),
        "breaths_per_minute": round(len(events) / (duration / 60), 2) if duration > 0 else 0,
        "avg_breath_duration_s": round(float(np.mean([e["duration_s"] for e in events])), 3) if events else 0,
        "avg_inter_breath_interval_s": round(float(np.mean(intervals)), 2) if intervals else 0,
        "min_inter_breath_interval_s": round(float(np.min(intervals)), 2) if intervals else 0,
        "max_inter_breath_interval_s": round(float(np.max(intervals)), 2) if intervals else 0,
        "avg_phrase_duration_s": round(float(np.mean(phrase_durations)), 2) if phrase_durations else 0,
        "longest_phrase_s": round(float(np.max(phrase_durations)), 2) if phrase_durations else 0,
        "depth_distribution": depths,
        "context_distribution": contexts,
        "breath_events": events,
        "phrase_durations": phrase_durations[:50],
    }

    # Print summary
    print(f"\n  BREATH DETECTION")
    print(f"  {'='*60}")
    print(f"  {len(events)} breaths in {duration:.0f}s ({results['breaths_per_minute']:.1f}/min)")
    print(f"  Avg breath duration: {results['avg_breath_duration_s']:.3f}s")
    print(f"  Avg phrase length: {results['avg_phrase_duration_s']:.1f}s")
    print(f"  Longest phrase: {results['longest_phrase_s']:.1f}s")

    print(f"\n  DEPTH: deep={depths['deep']}  normal={depths['normal']}  catch={depths['catch']}")
    print(f"  CONTEXT: between={contexts['between phrases']}  start={contexts['phrase start']}  end={contexts['phrase end']}")

    if events:
        print(f"\n  FIRST 10 BREATHS:")
        for e in events[:10]:
            print(f"    {e['label']:>5s}  [{e['depth']:>6s}]  {e['duration_s']:.3f}s  {e['avg_energy_db']:>6.1f}dB  {e['context']}")

    print(f"  {'='*60}")
    return results

def _empty_result(duration):
    return {
        "duration": round(duration, 2),
        "total_breaths": 0,
        "breaths_per_minute": 0,
        "avg_breath_duration_s": 0,
        "avg_inter_breath_interval_s": 0,
        "avg_phrase_duration_s": 0,
        "longest_phrase_s": 0,
        "depth_distribution": {"deep": 0, "normal": 0, "catch": 0},
        "context_distribution": {},
        "breath_events": [],
        "phrase_durations": [],
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python breath_detection.py <vocals.wav>")
        sys.exit(1)

    results = detect_breaths(sys.argv[1])
    out = sys.argv[1].rsplit('.', 1)[0] + '_breath.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, cls=NpEncoder)
    print(f"\nSaved: {out}")
