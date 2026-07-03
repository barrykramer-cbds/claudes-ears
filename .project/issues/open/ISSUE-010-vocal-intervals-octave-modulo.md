# ISSUE-010: Octave interval folded into unison by % 12, octave bucket is dead

**Severity**: LOW
**Type**: Bug
**Discovered By**: code-review-engineer
**Discovered During**: ad-hoc review
**Affected Files**: vocal_intervals.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

Interval classification reduces every interval modulo 12, then guards with a condition that
is always true:

```python
# vocal_intervals.py:69-71
interval_class = interval_semitones % 12
if interval_class <= 12:          # always true: result of % 12 is 0..11
    interval_counts[interval_class] += 1
```

`12 % 12 == 0`, so a true octave is counted as a unison. `interval_counts[12]` is therefore
never incremented, even though the profile loop iterates `for semitones in range(13)`
(:85) and `INTERVAL_NAMES[12]` ("octave") exists. The downstream power calculation reads
`interval_counts.get(12, 0)` (:111), which is always `0`, so octaves contribute nothing to
the "power" (fifths + unisons + octaves) tally and inflate the unison count instead.

## Reproduction / Evidence

Any pair of detected peaks 12 (or 24, 36, ...) semitones apart:

```
interval_semitones = 12  ->  interval_class = 12 % 12 = 0  ->  counted as "unison"
```

The "octave" row of the interval profile is permanently 0%; the `<= 12` branch never
filters anything (dead condition).

## Impact

Silently incorrect harmonic-character output: octaves are misreported as unisons and
dropped from the power-interval weighting. No crash; the analytic result is just wrong for
any vocal with octave doublings.

## Suggested Fix

Keep octaves distinct from unison (cap rather than wrap), or fold deliberately and remove
the dead branch:

```python
# Option A: preserve the octave bucket
interval_class = interval_semitones if interval_semitones <= 12 else (interval_semitones % 12) or 12
interval_counts[interval_class] += 1
```

If pitch-class folding is genuinely intended, drop `INTERVAL_NAMES[12]`, the `range(13)`
loop bound, and the `.get(12, 0)` term so the dead bucket is not misleading.

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
*Resolved: *
