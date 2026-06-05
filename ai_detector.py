#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude's Ears - AI Detection Scorer
Takes a track's analysis data and produces a probability score
for whether the vocal is AI-generated or human-performed.

Seven detection vectors, each independently validated across
3+ AI tracks and 20+ human tracks:

  1. Solo %        - AI avoids the spotlight
  2. Support %     - AI wraps itself in harmony
  3. Opposition %  - AI doesn't argue with itself
  4. Merge %       - AI collapses into self-unity
  5. Register span - AI lives in a compressed pitch box
  6. Register transitions - AI lacks intentional gear shifts
  7. Breathiness/breath ratio - AI has texture without physiology

Each vector produces a score from 0 (definitely human) to 1
(definitely AI). The final score is a weighted average.

NOTE: This is an architectural/relational detector, not a forensic
artifact classifier. At the top end of studio production polish it
cannot reliably discriminate; it characterizes vocal personality.
"""

import json, sys, os, numpy as np

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.bool_, bool)): return bool(obj)
        return super().default(obj)

def sigmoid(x, center, steepness):
    """Sigmoid function for smooth scoring. Returns 0-1."""
    return 1.0 / (1.0 + np.exp(-steepness * (x - center)))

def score_track(stem_folder, audio_path=None):
    """
    Score a track for AI detection across all available vectors.

    Args:
        stem_folder: path to the track's demucs output folder
        audio_path: path to original audio (for loading depth/emotion JSONs)

    Returns:
        dict with per-vector scores, overall probability, and verdict
    """
    track_name = os.path.basename(stem_folder)
    print(f"\n  AI DETECTION: {track_name}")
    print(f"  {'='*60}")

    vectors = {}
    weights = {}

    # --- VECTOR 1-4: Vocal Relationships ---
    rel_path = os.path.join(stem_folder, "vocals_relationships.json")
    if os.path.exists(rel_path):
        with open(rel_path, encoding='utf-8') as f:
            rel = json.load(f)
        rd = rel.get("relationship_distribution", {})

        solo = rd.get("solo", 0)
        support = rd.get("support", 0)
        opposition = rd.get("opposition", 0)
        merge = rd.get("merge", 0)

        # Vector 1: Solo % (human avg 16%, AI avg 5.2%)
        # Low solo = more AI-like. Sigmoid centered at 10%, steep.
        v1_score = 1.0 - sigmoid(solo, 10.0, 0.3)
        vectors["solo_pct"] = {
            "value": round(solo, 1),
            "score": round(v1_score, 3),
            "human_avg": 16.0,
            "ai_avg": 5.2,
            "signal": "low solo suggests AI",
        }
        weights["solo_pct"] = 1.5  # strong signal

        # Vector 2: Support % (human avg 30.6%, AI avg 54.6%)
        # High support = more AI-like. Sigmoid centered at 42%.
        v2_score = sigmoid(support, 42.0, 0.12)
        vectors["support_pct"] = {
            "value": round(support, 1),
            "score": round(v2_score, 3),
            "human_avg": 30.6,
            "ai_avg": 54.6,
            "signal": "high support suggests AI",
        }
        weights["support_pct"] = 1.5  # strong signal

        # Vector 3: Opposition % (human avg 2.5%, AI avg 0.8%)
        # Low opposition = more AI-like. Sigmoid centered at 1.5%.
        v3_score = 1.0 - sigmoid(opposition, 1.5, 1.5)
        vectors["opposition_pct"] = {
            "value": round(opposition, 1),
            "score": round(v3_score, 3),
            "human_avg": 2.5,
            "ai_avg": 0.8,
            "signal": "low opposition suggests AI",
        }
        weights["opposition_pct"] = 1.0

        # Vector 4: Merge % (human avg 1.3%, AI avg 5.5%)
        # High merge = more AI-like. Sigmoid centered at 3%.
        v4_score = sigmoid(merge, 3.0, 0.5)
        vectors["merge_pct"] = {
            "value": round(merge, 1),
            "score": round(v4_score, 3),
            "human_avg": 1.3,
            "ai_avg": 5.5,
            "signal": "high merge suggests AI",
        }
        weights["merge_pct"] = 0.8

    # --- VECTOR 5-6: Register Tracking ---
    reg_path = os.path.join(stem_folder, "vocals_register.json")
    if os.path.exists(reg_path):
        with open(reg_path, encoding='utf-8') as f:
            reg = json.load(f)

        span = reg.get("singer_range_high", 0) - reg.get("singer_range_low", 0)
        transitions = reg.get("total_transitions", 0)
        duration = reg.get("duration", 1)

        # Vector 5: Pitch span (human avg 394Hz, AI avg 126Hz)
        # Narrow span = more AI-like. Sigmoid centered at 250Hz.
        v5_score = 1.0 - sigmoid(span, 250.0, 0.015)
        vectors["pitch_span_hz"] = {
            "value": round(span, 0),
            "score": round(v5_score, 3),
            "human_avg": 394,
            "ai_avg": 126,
            "signal": "narrow pitch span suggests AI",
        }
        weights["pitch_span_hz"] = 1.2

        # Vector 6: Transitions per minute
        # This is tricky: AI can have HIGH transitions (noise) or LOW.
        # The key is transitions relative to span.
        # Human: meaningful transitions serving the lyric.
        # AI: either mechanical oscillation or very few.
        # Use transitions per octave of span as the metric.
        span_octaves = span / 200.0 if span > 0 else 1.0
        trans_per_min = transitions / (duration / 60.0) if duration > 0 else 0
        trans_density = trans_per_min / span_octaves if span_octaves > 0 else 0

        # Very high density (noise) or very low density (static) = AI
        # Human sweet spot: 2-8 transitions/min/octave
        if trans_density < 1.0 or trans_density > 15.0:
            v6_score = 0.7  # suspicious
        elif trans_density < 2.0 or trans_density > 10.0:
            v6_score = 0.4  # mildly suspicious
        else:
            v6_score = 0.15  # human range

        vectors["register_behavior"] = {
            "value": round(trans_density, 2),
            "score": round(v6_score, 3),
            "transitions": transitions,
            "span_octaves": round(span_octaves, 2),
            "signal": "extreme transition density suggests AI",
        }
        weights["register_behavior"] = 0.8

    # --- VECTOR 7: Breathiness/Breath Ratio ---
    breath_path = os.path.join(stem_folder, "vocals_breath.json")
    stem_path = os.path.join(stem_folder, "stem_analysis.json")

    if os.path.exists(breath_path) and os.path.exists(stem_path):
        with open(breath_path, encoding='utf-8') as f:
            breath = json.load(f)
        with open(stem_path, encoding='utf-8') as f:
            stem = json.load(f)

        breathiness = stem.get("vocals", {}).get("breathiness", 0)
        breath_count = breath.get("total_breaths", 0)
        duration = breath.get("duration", 1)
        breaths_per_min = breath.get("breaths_per_minute", 0)

        # The ratio of breath events to breathiness level
        # Human: high breathiness = many breath events (correlated)
        # AI: can have high breathiness with zero events (texture without physiology)
        if breathiness > 0.01:
            breath_ratio = breaths_per_min / (breathiness * 100)
        else:
            breath_ratio = breaths_per_min  # low breathiness track

        # Zero breaths with any breathiness = very AI
        # Zero breaths with zero breathiness = could be studio-cleaned human
        if breath_count == 0 and breathiness > 0.03:
            v7_score = 0.9  # high breathiness, no events = strong AI signal
        elif breath_count == 0 and breathiness > 0.01:
            v7_score = 0.6  # some breathiness, no events = moderate signal
        elif breath_count == 0:
            v7_score = 0.4  # low breathiness, no events = could be studio
        elif breath_ratio < 0.5:
            v7_score = 0.5  # low ratio = suspicious
        else:
            v7_score = 0.1  # normal breath/breathiness correlation = human

        # Deep breath events are strong human signals
        deep = breath.get("depth_distribution", {}).get("deep", 0)
        if deep > 0:
            v7_score *= 0.5  # deep breaths = definitely human, halve the AI score

        vectors["breath_physiology"] = {
            "value": round(breath_ratio, 3),
            "score": round(v7_score, 3),
            "breathiness": round(breathiness, 4),
            "breath_events": breath_count,
            "deep_breaths": deep,
            "signal": "breathiness without breath events suggests AI",
        }
        weights["breath_physiology"] = 2.0  # strongest signal

    # --- FINAL SCORE ---
    if not vectors:
        print("  No analysis data found.")
        return None

    # Weighted average
    total_weight = sum(weights.values())
    weighted_sum = sum(vectors[k]["score"] * weights[k] for k in vectors if k in weights)
    overall = weighted_sum / total_weight if total_weight > 0 else 0.5

    # Production-aware verdict (v2)
    solo_val = vectors.get("solo_pct", {}).get("value", 50)
    supp_val = vectors.get("support_pct", {}).get("value", 0)
    breath_events = vectors.get("breath_physiology", {}).get("breath_events", -1)
    breathiness_val = vectors.get("breath_physiology", {}).get("breathiness", 0)
    deep_breaths = vectors.get("breath_physiology", {}).get("deep_breaths", 0)

    heavily_produced = (supp_val > 50 and solo_val < 5 and breath_events == 0)
    breathiness_paradox = (breathiness_val > 0.03 and breath_events == 0)
    has_deep_breaths = deep_breaths > 0

    if len(vectors) < 4:
        verdict = f"INSUFFICIENT DATA ({len(vectors)}/7)"
        confidence = "none"
    elif has_deep_breaths and overall >= 0.4:
        verdict = "HEAVILY PRODUCED HUMAN"
        confidence = "moderate"
    elif has_deep_breaths:
        verdict = "HUMAN"
        confidence = "high"
    elif breathiness_paradox and overall >= 0.55:
        verdict = "LIKELY AI"
        confidence = "high"
    elif heavily_produced and overall >= 0.55:
        verdict = "AI OR HEAVY PRODUCTION"
        confidence = "low"
    elif overall >= 0.7:
        verdict = "LIKELY AI"
        confidence = "high"
    elif overall >= 0.55:
        verdict = "POSSIBLY AI"
        confidence = "moderate"
    elif overall >= 0.4:
        verdict = "INCONCLUSIVE"
        confidence = "low"
    elif overall >= 0.25:
        verdict = "LIKELY HUMAN"
        confidence = "moderate"
    else:
        verdict = "HUMAN"
        confidence = "high"

    results = {
        "track": track_name,
        "overall_score": round(overall, 3),
        "verdict": verdict,
        "confidence": confidence,
        "vectors": vectors,
        "weights": {k: round(v, 1) for k, v in weights.items()},
        "vectors_available": len(vectors),
        "vectors_possible": 7,
    }

    # Print report
    print(f"\n  DETECTION VECTORS:")
    for name, v in vectors.items():
        bar_len = int(v["score"] * 20)
        bar = "#" * bar_len + "." * (20 - bar_len)
        label = "AI" if v["score"] > 0.5 else "HU"
        print(f"    [{label}] {name:<22s}  [{bar}] {v['score']:.2f}  val={v['value']}")

    print(f"\n  {'='*60}")
    print(f"  OVERALL: {overall:.3f}  ->  {verdict} (confidence: {confidence})")
    print(f"  Vectors: {len(vectors)}/7 available")
    print(f"  {'='*60}")

    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ai_detector.py <stems_folder> [audio_path]")
        print("  stems_folder: path to demucs output for this track")
        print("  audio_path: optional path to original audio file")
        print()
        print("Batch mode:")
        print("  python ai_detector.py --batch")
        print("  Scores ALL tracks under CLAUDES_EARS_STEMS")
        sys.exit(1)

    if sys.argv[1] == "--batch":
        stems_base = os.environ.get("CLAUDES_EARS_STEMS", os.path.join("stems", "htdemucs"))
        music_base = os.environ.get("CLAUDES_EARS_MUSIC", "music")
        all_results = []

        for d in sorted(os.listdir(stems_base)):
            stem_path = os.path.join(stems_base, d)
            if not os.path.isdir(stem_path):
                continue

            # Try to find matching audio file
            audio_path = None
            for ext in ['.mp3', '.wav', '.flac']:
                candidate = os.path.join(music_base, d + ext)
                if os.path.exists(candidate):
                    audio_path = candidate
                    break

            result = score_track(stem_path, audio_path)
            if result:
                all_results.append(result)

        # Summary table
        print(f"\n\n{'='*70}")
        print(f"  AI DETECTION — FULL COLLECTION SUMMARY")
        print(f"{'='*70}")
        print(f"{'Track':<40s} {'Score':>6s}  {'Verdict':<15s}")
        print(f"{'-'*65}")

        for r in sorted(all_results, key=lambda x: -x["overall_score"]):
            print(f"{r['track'][:40]:<40s} {r['overall_score']:>5.3f}  {r['verdict']:<15s}")

        # Save batch results
        out = os.path.join(stems_base, "ai_detection_scores.json")
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, cls=NpEncoder)
        print(f"\nSaved: {out}")

    else:
        audio = sys.argv[2] if len(sys.argv) > 2 else None
        result = score_track(sys.argv[1], audio)
        if result:
            out = os.path.join(sys.argv[1], "ai_detection.json")
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, cls=NpEncoder)
            print(f"\nSaved: {out}")
