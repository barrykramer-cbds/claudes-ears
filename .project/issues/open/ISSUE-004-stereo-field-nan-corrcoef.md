# ISSUE-004: Silent/DC stereo channel yields NaN correlation, wrong label, and invalid JSON

**Severity**: MEDIUM
**Type**: Bug
**Discovered By**: code-review-engineer
**Discovered During**: ad-hoc review
**Affected Files**: stereo_field.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

`stereo_field.py:64` computes Pearson correlation between L and R without guarding for a
zero-variance channel:

```python
# stereo_field.py:63-72
min_len = min(len(left), len(right))
correlation = float(np.corrcoef(left[:min_len], right[:min_len])[0, 1])
results["lr_correlation"] = round(correlation, 4)
results["correlation_desc"] = (
    "near-mono (L~=R)" if correlation > 0.95 else
    ...
    "phase effects present"   # <-- fall-through when correlation is NaN
)
```

If either channel is constant (silence, DC offset, a fully muted side), its variance is 0
and `np.corrcoef` returns `nan` (the RuntimeWarning is suppressed by
`warnings.filterwarnings('ignore')`). `round(nan, 4)` is `nan`; every `correlation > x`
comparison is `False`, so the description falls through to "phase effects present" — a
confidently wrong label for silence.

`freq_interaction.py:75` guards this exact case with an `np.std(...) > 0` check;
`stereo_field.py` does not.

## Reproduction / Evidence

Feed a silent or mono-as-stereo file (both channels identical constant, or one channel
muted). `np.corrcoef` of a zero-variance vector returns `nan`. The written `_stereo.json`
then contains:

```json
"lr_correlation": NaN,
"correlation_desc": "phase effects present"
```

`NaN` is not valid JSON per RFC 8259. Python's own `json.load` accepts it (so
`story_reader.py:227` round-trips it), but any strict parser — jq, browsers, Go, Rust
serde, most API gateways — rejects the file.

## Impact

(1) Mislabeled stereo analysis for silent/edge tracks. (2) Output files that are not
spec-valid JSON, breaking interoperability and any non-Python consumer. The same
`allow_nan=True` default affects every module that can produce NaN (see ISSUE-005).

## Suggested Fix

Guard the variance and emit a finite sentinel:

```python
if np.std(left[:min_len]) > 0 and np.std(right[:min_len]) > 0:
    correlation = float(np.corrcoef(left[:min_len], right[:min_len])[0, 1])
else:
    correlation = 0.0  # undefined for a silent/DC channel
```

Additionally, dump JSON with `json.dump(results, f, allow_nan=False)` so any remaining
NaN fails loudly at write time instead of silently producing invalid output.

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
*Resolved: *
