# ISSUE-002: Operator-precedence bug crashes vocal_narrative on silent piptrack frames

**Severity**: HIGH
**Type**: Bug
**Discovered By**: code-review-engineer
**Discovered During**: ad-hoc review
**Affected Files**: vocal_narrative.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

`vocal_narrative.py:92` builds an array index with a conditional expression whose
precedence makes the `else` branch evaluate to the integer `0` instead of an empty
selection. When a piptrack frame has all-zero magnitudes, the index becomes scalar
`0`, reducing `strong` to a single np.float64, and the next line crashes.

```python
# vocal_narrative.py:92-93
strong = frame_pitches[frame_mags > np.percentile(frame_mags[frame_mags > 0], 50) if frame_mags.max() > 0 else 0]
strong = strong[strong > 80]  # above 80 Hz
```

Python parses the index as `(mask) if frame_mags.max() > 0 else 0`. The author clearly
intended the ternary only to guard the empty-`percentile` case, but `else 0` is a valid
integer index:

- `frame_mags.max() > 0` (True): index is a boolean mask -> `strong` is a 1-D array. Fine.
- `frame_mags.max() == 0` (all-zero magnitudes): index is `0` -> `strong = frame_pitches[0]`
  is a **scalar**. Line 93 then evaluates `strong[strong > 80]`, i.e. indexing a scalar,
  which raises `IndexError: invalid index to scalar variable.`

## Reproduction / Evidence

A piptrack frame with no detected pitch peak has an all-zero magnitude column
(`frame_mags.max() == 0`). This occurs routinely inside otherwise non-silent 3-second
segments — vocal rests, unvoiced consonants, breaths. Any track containing such a frame
crashes the module:

```
IndexError: invalid index to scalar variable.
  at vocal_narrative.py:93  strong = strong[strong > 80]
```

The correct pattern is used in `vocal_relationships.py:108`, which assigns the full
ternary to a variable before indexing — that module is unaffected.

## Impact

`vocal_narrative.py` (lead/chorus separation, call-and-response — a stated core
differentiator) crashes on realistic vocal input. In `full_perception.py` the step is
`optional=True`, so the pipeline continues but silently loses vocal-narrative output for
most real tracks. Run standalone, it aborts.

## Suggested Fix

Compute the mask once, guarding the empty case explicitly so the `else` yields a real
(empty) selection, not an integer:

```python
if frame_mags.max() > 0:
    thresh = np.percentile(frame_mags[frame_mags > 0], 50)
    strong = frame_pitches[frame_mags > thresh]
else:
    strong = frame_pitches[frame_mags > 0]  # empty array, not scalar 0
strong = strong[strong > 80]
```

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
*Resolved: *
