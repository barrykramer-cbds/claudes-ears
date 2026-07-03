# ISSUE-006: NMF crashes on short audio or unvalidated n_components argument

**Severity**: MEDIUM
**Type**: Bug
**Discovered By**: code-review-engineer
**Discovered During**: ad-hoc review
**Affected Files**: timbral_decomposition.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

`timbral_decomposition.py:100-101` runs `NMF(init='nndsvd')` with `n_components` taken
directly from `sys.argv[2]` with no bounds check against the spectrogram size:

```python
# timbral_decomposition.py:95-101
S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
...
model = NMF(n_components=n_components, init='nndsvd', max_iter=300, random_state=42)
W = model.fit_transform(S)   # S: (freq_bins, n_frames)
```

scikit-learn's NMF requires `n_components <= min(n_samples, n_features)`. With
`init='nndsvd'`, the truncated-SVD initialization indexes singular vectors up to
`n_components`; when the number of STFT frames `n_frames < n_components`, this raises an
error (IndexError / ValueError) and the module aborts.

## Reproduction / Evidence

Two reachable triggers:

1. Short input at the default `n_components=4`: a clip under ~0.1s yields fewer than 4
   STFT frames at hop=512 -> `n_frames < 4` -> NMF fails.
2. Bad CLI argument, no validation: `python timbral_decomposition.py other.wav 5000`
   sets `n_components=5000 >> n_frames` -> immediate crash. `full_perception.py:126`
   invokes this module with a hardcoded `4`, but the standalone path accepts any integer.

## Impact

Crash on short stems and on any out-of-range `n_components`. In the orchestrated pipeline
the step is `optional=True` so the run continues, but timbral output is lost; standalone
invocation aborts with an opaque sklearn traceback.

## Suggested Fix

Clamp `n_components` to the data and validate the CLI argument:

```python
n_frames = S.shape[1]
n_components = max(1, min(n_components, n_frames, S.shape[0]))
if n_frames < 2:
    print("  Audio too short for NMF decomposition; skipping.")
    return None
```

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
*Resolved: *
