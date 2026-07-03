# ISSUE-005: temporal_segmentation writes NaN into JSON for short audio (<3 windows)

**Severity**: MEDIUM
**Type**: Bug
**Discovered By**: code-review-engineer
**Discovered During**: ad-hoc review
**Affected Files**: temporal_segmentation.py, emotional_trajectory.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

The narrative-arc summary divides the snapshot list into thirds with integer division.
When there are fewer than 3 snapshots, `len(snaps)//3 == 0`, so the first/middle slices
are empty and `np.mean([])` returns `nan`:

```python
# temporal_segmentation.py:120-126 (approx)
t = len(snaps) // 3
e1 = np.mean([s["rms_p90"] for s in snaps[:t]])      # snaps[:0] -> [] -> nan
e2 = np.mean([s["rms_p90"] for s in snaps[t:2*t]])   # snaps[0:0] -> [] -> nan
...
```

The RuntimeWarning ("Mean of empty slice") is suppressed by
`warnings.filterwarnings('ignore')`, so the NaN propagates silently into the
`narrative.arc` fields and is serialized with the default `allow_nan=True`.

## Reproduction / Evidence

A ~20-second clip at the default window/hop (15s / 5s) produces ~2 snapshots -> `t == 0`
-> `e1`, `e2`, `t1`, `t2` are all NaN. The written `_temporal.json` contains bare `NaN`
tokens, which are invalid JSON (RFC 8259). `emotional_trajectory.py:55-59` then loads this
file as its only input; while Python's `json.load` tolerates `NaN`, any strict consumer
does not, and the NaN values flow into `generate_narrative`.

## Impact

Invalid JSON output and NaN-poisoned narrative fields for short tracks / clips. Because
`emotional_trajectory.py` is the sole consumer of `_temporal.json`, the corruption
cascades to `_emotion.json` and onward to `story_reader.py`.

## Suggested Fix

Guard the thirds computation and skip the arc when there are too few windows:

```python
n = len(snaps)
if n >= 3:
    t = n // 3
    e1 = float(np.mean([s["rms_p90"] for s in snaps[:t]]))
    ...
else:
    arc = {}  # not enough data for a three-act arc
```

Also serialize with `allow_nan=False` so any residual NaN fails loudly instead of writing
invalid JSON.

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
*Resolved: *
