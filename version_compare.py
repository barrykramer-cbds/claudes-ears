#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude's Ears - Studio vs Live / Version Comparison
Takes two versions of the same song and generates a delta report
across every dimension the pipeline measures.

The delta IS the fingerprint:
  - Studio vs Live: the producer's invisible hand
  - Movie vs Human: the digital engineer's manipulation
  - Original vs Cover: what the new performer changed

Every difference between versions reveals a decision someone made.
"""

import json, sys, os, numpy as np

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.bool_, bool)): return bool(obj)
        return super().default(obj)

def load_json(path):
    """Load a JSON file if it exists."""
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return None

def delta(a, b, label=""):
    """Compute delta between two values with direction."""
    if a is None or b is None:
        return None
    diff = b - a
    pct = (diff / abs(a) * 100) if a != 0 else 0
    return {"version_a": round(a, 4), "version_b": round(b, 4),
            "delta": round(diff, 4), "pct_change": round(pct, 1)}

def compare_versions(audio_a, audio_b, label_a="Version A", label_b="Version B"):
    """
    Compare two versions of the same track across all pipeline dimensions.

    Args:
        audio_a: path to first audio file (e.g., studio version)
        audio_b: path to second audio file (e.g., live version)
        label_a: human label for version A
        label_b: human label for version B
    """
    stems_base = os.environ.get("CLAUDES_EARS_STEMS", os.path.join("stems", "htdemucs"))

    name_a = os.path.splitext(os.path.basename(audio_a))[0]
    name_b = os.path.splitext(os.path.basename(audio_b))[0]
    stems_a = os.path.join(stems_base, name_a)
    stems_b = os.path.join(stems_base, name_b)

    print(f"\n{'='*70}")
    print(f"  VERSION COMPARISON")
    print(f"  A: {label_a} ({name_a})")
    print(f"  B: {label_b} ({name_b})")
    print(f"{'='*70}")

    report = {
        "version_a": {"label": label_a, "file": name_a},
        "version_b": {"label": label_b, "file": name_b},
        "deltas": {},
    }

    # --- STEM ANALYSIS ---
    stem_a = load_json(os.path.join(stems_a, "stem_analysis.json"))
    stem_b = load_json(os.path.join(stems_b, "stem_analysis.json"))

    if stem_a and stem_b:
        print(f"\n  VOCAL CHARACTERISTICS")
        print(f"  {'-'*60}")

        vocal_deltas = {}
        fields = [
            ("pitch_mean_hz", "Pitch (Hz)"),
            ("pitch_range_semitones", "Range (st)"),
            ("vocal_melodic_entropy", "Entropy"),
            ("breathiness", "Breathiness"),
        ]
        for field, label in fields:
            va = stem_a["vocals"].get(field, 0)
            vb = stem_b["vocals"].get(field, 0)
            d = delta(va, vb)
            vocal_deltas[field] = d
            if d:
                arrow = ">>" if d["delta"] > 0 else "<<" if d["delta"] < 0 else "=="
                print(f"    {label:<20s}  {d['version_a']:>8.4f}  {arrow}  {d['version_b']:>8.4f}  ({d['pct_change']:+.1f}%)")

        report["deltas"]["vocals"] = vocal_deltas

        # Drums
        drum_deltas = {}
        drum_fields = [
            ("tempo_bpm", "Tempo (BPM)"),
            ("beat_regularity", "Regularity"),
            ("onsets_per_second", "Onsets/sec"),
        ]
        print(f"\n  RHYTHM")
        print(f"  {'-'*60}")
        for field, label in drum_fields:
            va = stem_a["drums"].get(field, 0)
            vb = stem_b["drums"].get(field, 0)
            d = delta(va, vb)
            drum_deltas[field] = d
            if d:
                arrow = ">>" if d["delta"] > 0 else "<<" if d["delta"] < 0 else "=="
                print(f"    {label:<20s}  {d['version_a']:>8.4f}  {arrow}  {d['version_b']:>8.4f}  ({d['pct_change']:+.1f}%)")

        # Kick balance
        ka = stem_a["drums"]["kit_balance"].get("kick", 0)
        kb = stem_b["drums"]["kit_balance"].get("kick", 0)
        d = delta(ka, kb)
        drum_deltas["kick_balance"] = d
        if d:
            arrow = ">>" if d["delta"] > 0 else "<<" if d["delta"] < 0 else "=="
            print(f"    {'Kick %':<20s}  {d['version_a']:>8.1f}  {arrow}  {d['version_b']:>8.1f}  ({d['pct_change']:+.1f}%)")

        report["deltas"]["drums"] = drum_deltas

    # --- VOCAL RELATIONSHIPS ---
    rel_a = load_json(os.path.join(stems_a, "vocals_relationships.json"))
    rel_b = load_json(os.path.join(stems_b, "vocals_relationships.json"))

    if rel_a and rel_b:
        print(f"\n  VOCAL RELATIONSHIPS (the story between voices)")
        print(f"  {'-'*60}")

        rel_deltas = {}
        for rel_type in ["solo", "support", "dialogue", "opposition", "merge", "withdraw"]:
            va = rel_a["relationship_distribution"].get(rel_type, 0)
            vb = rel_b["relationship_distribution"].get(rel_type, 0)
            d = delta(va, vb)
            rel_deltas[rel_type] = d
            if d:
                arrow = ">>" if d["delta"] > 0 else "<<" if d["delta"] < 0 else "=="
                significance = ""
                if abs(d["delta"]) > 10:
                    significance = " *** MAJOR"
                elif abs(d["delta"]) > 5:
                    significance = " ** notable"
                print(f"    {rel_type:<14s}  {d['version_a']:>6.1f}%  {arrow}  {d['version_b']:>6.1f}%  (delta {d['delta']:+.1f}){significance}")

        report["deltas"]["vocal_relationships"] = rel_deltas

    # --- REGISTER TRACKING ---
    reg_a = load_json(os.path.join(stems_a, "vocals_register.json"))
    reg_b = load_json(os.path.join(stems_b, "vocals_register.json"))

    if reg_a and reg_b:
        print(f"\n  REGISTER TRACKING")
        print(f"  {'-'*60}")

        reg_deltas = {}
        span_a = reg_a.get("singer_range_high", 0) - reg_a.get("singer_range_low", 0)
        span_b = reg_b.get("singer_range_high", 0) - reg_b.get("singer_range_low", 0)
        d = delta(span_a, span_b)
        reg_deltas["pitch_span"] = d
        if d:
            arrow = ">>" if d["delta"] > 0 else "<<" if d["delta"] < 0 else "=="
            print(f"    {'Pitch span (Hz)':<20s}  {d['version_a']:>8.0f}  {arrow}  {d['version_b']:>8.0f}  ({d['pct_change']:+.1f}%)")

        d = delta(reg_a.get("total_transitions", 0), reg_b.get("total_transitions", 0))
        reg_deltas["transitions"] = d
        if d:
            arrow = ">>" if d["delta"] > 0 else "<<" if d["delta"] < 0 else "=="
            print(f"    {'Transitions':<20s}  {d['version_a']:>8.0f}  {arrow}  {d['version_b']:>8.0f}  ({d['pct_change']:+.1f}%)")

        for reg_type in ["chest", "head", "falsetto", "fry"]:
            va = reg_a.get("register_distribution", {}).get(reg_type, 0)
            vb = reg_b.get("register_distribution", {}).get(reg_type, 0)
            d = delta(va, vb)
            reg_deltas[reg_type] = d
            if d and (d["version_a"] > 0 or d["version_b"] > 0):
                arrow = ">>" if d["delta"] > 0 else "<<" if d["delta"] < 0 else "=="
                print(f"    {reg_type:<20s}  {d['version_a']:>7.1f}%  {arrow}  {d['version_b']:>7.1f}%  (delta {d['delta']:+.1f})")

        report["deltas"]["register"] = reg_deltas

    # --- DEPTH / REVERB ---
    depth_a = load_json(audio_a.rsplit('.', 1)[0] + '_depth.json')
    depth_b = load_json(audio_b.rsplit('.', 1)[0] + '_depth.json')

    if depth_a and depth_b:
        print(f"\n  DEPTH / SPACE")
        print(f"  {'-'*60}")

        depth_deltas = {}
        depth_fields = [
            ("spectral_persistence", "Persistence"),
            ("pre_delay_ms", "Pre-delay (ms)"),
            ("wetness_index", "Wetness"),
            ("spectral_flatness_mean", "Flatness"),
        ]
        for field, label in depth_fields:
            va = depth_a.get(field, 0)
            vb = depth_b.get(field, 0)
            d = delta(va, vb)
            depth_deltas[field] = d
            if d:
                arrow = ">>" if d["delta"] > 0 else "<<" if d["delta"] < 0 else "=="
                print(f"    {label:<20s}  {d['version_a']:>8.4f}  {arrow}  {d['version_b']:>8.4f}  ({d['pct_change']:+.1f}%)")

        report["deltas"]["depth"] = depth_deltas

    # --- GROOVE TIMING ---
    groove_a = load_json(os.path.join(stems_a, "drums_groove.json"))
    groove_b = load_json(os.path.join(stems_b, "drums_groove.json"))

    if groove_a and groove_b:
        print(f"\n  GROOVE / FEEL")
        print(f"  {'-'*60}")

        groove_deltas = {}
        groove_fields = [
            ("mean_deviation_ms", "Beat deviation (ms)"),
            ("swing_ratio", "Swing ratio"),
        ]
        for field, label in groove_fields:
            va = groove_a.get(field, 0)
            vb = groove_b.get(field, 0)
            d = delta(va, vb)
            groove_deltas[field] = d
            if d:
                arrow = ">>" if d["delta"] > 0 else "<<" if d["delta"] < 0 else "=="
                print(f"    {label:<20s}  {d['version_a']:>8.3f}  {arrow}  {d['version_b']:>8.3f}  ({d['pct_change']:+.1f}%)")

        # Feel labels
        feel_a = groove_a.get("feel", "unknown")
        feel_b = groove_b.get("feel", "unknown")
        groove_deltas["feel_change"] = {"version_a": feel_a, "version_b": feel_b, "changed": feel_a != feel_b}
        if feel_a != feel_b:
            print(f"    {'Feel':<20s}  \"{feel_a[:30]}\" >> \"{feel_b[:30]}\"")

        report["deltas"]["groove"] = groove_deltas

    # --- HARMONIC RHYTHM ---
    hr_a = load_json(audio_a.rsplit('.', 1)[0] + '_harmonic_rhythm.json')
    hr_b = load_json(audio_b.rsplit('.', 1)[0] + '_harmonic_rhythm.json')

    if hr_a and hr_b:
        print(f"\n  HARMONIC RHYTHM")
        print(f"  {'-'*60}")

        hr_deltas = {}
        hr_fields = [
            ("avg_changes_per_bar", "Avg changes/bar"),
            ("max_changes_per_bar", "Max changes/bar"),
            ("total_accel_events", "Accel events"),
        ]
        for field, label in hr_fields:
            va = hr_a.get(field, 0)
            vb = hr_b.get(field, 0)
            d = delta(va, vb)
            hr_deltas[field] = d
            if d:
                arrow = ">>" if d["delta"] > 0 else "<<" if d["delta"] < 0 else "=="
                print(f"    {label:<20s}  {d['version_a']:>8.2f}  {arrow}  {d['version_b']:>8.2f}  ({d['pct_change']:+.1f}%)")

        arc_a = hr_a.get("harmonic_arc", "unknown")
        arc_b = hr_b.get("harmonic_arc", "unknown")
        hr_deltas["arc_change"] = {"version_a": arc_a, "version_b": arc_b, "changed": arc_a != arc_b}
        if arc_a != arc_b:
            print(f"    {'Arc':<20s}  \"{arc_a[:25]}\" >> \"{arc_b[:25]}\"")

        report["deltas"]["harmonic_rhythm"] = hr_deltas

    # --- EMOTIONAL TRAJECTORY ---
    emo_a = load_json(audio_a.rsplit('.', 1)[0] + '_emotion.json')
    emo_b = load_json(audio_b.rsplit('.', 1)[0] + '_emotion.json')

    if emo_a and emo_b:
        print(f"\n  EMOTIONAL TRAJECTORY")
        print(f"  {'-'*60}")

        emo_deltas = {}
        emo_fields = [
            ("total_phases", "Phases"),
            ("total_transitions", "Transitions"),
            ("unique_states", "Unique states"),
        ]
        for field, label in emo_fields:
            va = emo_a.get(field, 0)
            vb = emo_b.get(field, 0)
            d = delta(va, vb)
            emo_deltas[field] = d
            if d:
                arrow = ">>" if d["delta"] > 0 else "<<" if d["delta"] < 0 else "=="
                print(f"    {label:<20s}  {d['version_a']:>8.0f}  {arrow}  {d['version_b']:>8.0f}  ({d['pct_change']:+.1f}%)")

        report["deltas"]["emotion"] = emo_deltas

    # --- SUMMARY: BIGGEST DELTAS ---
    print(f"\n  {'='*70}")
    print(f"  FINGERPRINT SUMMARY — What changed between versions")
    print(f"  {'='*70}")

    # Collect all deltas and sort by magnitude
    all_deltas = []
    for category, deltas in report["deltas"].items():
        for metric, d in deltas.items():
            if isinstance(d, dict) and "delta" in d and d["delta"] is not None:
                all_deltas.append({
                    "category": category,
                    "metric": metric,
                    "abs_delta": abs(d["delta"]),
                    "delta": d["delta"],
                    "pct": d.get("pct_change", 0),
                    "a": d["version_a"],
                    "b": d["version_b"],
                })

    # Sort by percentage change magnitude
    all_deltas.sort(key=lambda x: abs(x["pct"]), reverse=True)

    print(f"\n  TOP CHANGES (by % magnitude):")
    for i, d in enumerate(all_deltas[:10]):
        direction = "increased" if d["delta"] > 0 else "decreased"
        print(f"    {i+1:>2}. {d['category']}/{d['metric']}: {d['a']:.3f} -> {d['b']:.3f} ({d['pct']:+.1f}%) {direction}")

    report["fingerprint_top_changes"] = all_deltas[:10]

    print(f"\n{'='*70}")
    return report

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Claude's Ears -- Version Comparison")
    parser.add_argument("audio_a", help="Path to version A (e.g., studio)")
    parser.add_argument("audio_b", help="Path to version B (e.g., live)")
    parser.add_argument("--label-a", default="Version A", help="Label for version A")
    parser.add_argument("--label-b", default="Version B", help="Label for version B")
    args = parser.parse_args()

    report = compare_versions(args.audio_a, args.audio_b,
                              label_a=args.label_a, label_b=args.label_b)

    if report:
        out = os.path.join(os.path.dirname(args.audio_a),
                          f"comparison_{os.path.splitext(os.path.basename(args.audio_a))[0]}_vs_{os.path.splitext(os.path.basename(args.audio_b))[0]}.json")
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, cls=NpEncoder)
        print(f"\nSaved: {out}")
