# ISSUE-001: Shell injection via subprocess.run(shell=True) with interpolated paths

**Severity**: HIGH
**Type**: Security
**Discovered By**: code-review-engineer
**Discovered During**: ad-hoc review
**Affected Files**: full_perception.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

`full_perception.py` builds every pipeline command as an f-string and executes it
through a shell. Untrusted, attacker-influenceable strings are interpolated directly
into the command line with no escaping or argument separation.

```python
# full_perception.py:31
result = subprocess.run(cmd, shell=True, capture_output=False, timeout=600)
```

`cmd` is assembled throughout `full_perception()` / `batch_process()`, e.g.:

```python
# :80-81
f'"{py}" "{WORKSPACE}/run_demucs.py" "{audio_path}"'
# :186-188
story_cmd = f'"{py}" "{WORKSPACE}/story_reader.py" "{audio_path}" --stems "{stem_folder}"'
if artist and title:
    story_cmd += f' --artist "{artist}" --title "{title}"'
```

The interpolated values are all untrusted:
- `audio_path` — comes from `sys.argv` or `glob.glob(... "*.mp3")` (a filename on disk).
- `stem_folder` — derived from the basename, or from `glob.glob` matches (:92-94).
- `artist` / `title` — split from the filename by `parse_artist_title()` (:51-62).

The surrounding double-quotes do not make this safe: a double-quote character in any
interpolated value closes the quote and begins a new shell token. Command substitution
(`$(...)`, backticks) and metacharacters (`;`, `|`, `&`, `>`) are likewise honored.

## Reproduction / Evidence

Worst case is `--batch` mode, where the injection trigger is simply a filename present
in the music directory (no interactive argument needed):

```
# A file named exactly this in the batch folder:
"; rm -rf "$HOME"; echo pwned - x.mp3

# batch_process() globs it (:218), then full_perception() interpolates it into cmd
# (:81 etc.), subprocess.run(..., shell=True) executes the injected commands.
```

Even a benign filename containing a double-quote or `$()` breaks command parsing or
executes substitutions. Because `audio_path`, `artist`, and `title` all flow into the
same `shell=True` call, every step in the pipeline is an injection sink.

This also violates `.claude/rules/security.md` ("No shell injection", "never trust
input — validate everything").

## Impact

Arbitrary command execution in the context of the user running the pipeline. In batch
mode the attack surface is any filename that lands in the watched music folder (e.g. a
maliciously named download from `yt-dlp`). Full local compromise: file deletion,
exfiltration, persistence.

## Suggested Fix

Stop using a shell. Pass argument lists and drop `shell=True`:

```python
def run_step(name, argv, optional=False):
    result = subprocess.run(argv, timeout=600)  # argv is a list, no shell

# callers build lists, not strings:
run_step("Stem Separation", [py, f"{WORKSPACE}/run_demucs.py", audio_path])
story_argv = [py, f"{WORKSPACE}/story_reader.py", audio_path, "--stems", stem_folder]
if artist and title:
    story_argv += ["--artist", artist, "--title", title]
```

With a list and no shell, none of the interpolated values can break out of their
argument boundary. If a shell is genuinely required for some step, use
`shlex.quote()` on every interpolated value — but the list form is strictly preferred.

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
*Resolved: *
