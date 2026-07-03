# Session Handoff — 2026-07-03 (App is live; real run needs a GPU)

> Read this first. **Direction now: Phase 4.1.7 — get the stack running on the MacBook Pro (MPS)**,
> then finish the first real run (4.1.1) there. CPU separation on this box is a confirmed no-go.

## Where we are

- **Remotes consolidated:** the `ul0gic` fork is deleted. `origin` = Barry's repo
  (`barrykramer-cbds/claudes-ears`) with direct push access. Work stays on `feat/desktop-app`,
  merged straight into `origin/main` when done — **no PR gate**, so run the deferred adversarial
  review before merging.
- **Committed + pushed on `origin/feat/desktop-app`** (all gates green at each commit):
  - `818f169` — randomId() UUID fallback; DropZone removed for a quiet empty state.
  - `3391a04` — `.project/` planning docs now tracked in the repo (un-gitignored; `.claude/` stays local).
  - `3547a8a` — **4.4.6 + 4.4.7**: YouTube URL ingest (`POST /jobs` takes exactly one of
    `audio_path` | `source_url`; yt-dlp → music dir; `download` SSE step with percent before the 21
    pipeline steps) + mock retired (`VITE_USE_MOCK` default false), library hydrates from
    `GET /library`, dashboard of analyzed tracks, Add Track modal (YouTube URL | file picker).
    Also: `claudes-ears-serve` console script (uvicorn on 127.0.0.1:8765) and a fixed SSE race
    (terminal sentinel could overtake the final event).
  - `37def1d` — CORS middleware for browser-dev origins (`CLAUDES_EARS_DEV_PORTS`, default 5173).
  - `f456b8a` — vite dev proxy (`/jobs`, `/library` → 127.0.0.1:8765); renderer fetches relative
    paths, so serving the UI on a LAN host works. Electron will inject an absolute base URL.

## The first real run (4.1.1) — attempted, aborted

End-to-end via the app worked: YouTube download → music dir → demucs separation started, live SSE
progress in the UI. **User aborted: CPU separation is unusably slow** (~3.5 min per demucs pass over
31 chunks, several passes per track). **The only GPU in the house is a MacBook Pro** → new task
**4.1.7**: torch **MPS** on Apple Silicon (audio-separator + faster-whisper device selection),
macOS-first packaging in Phase 6. Resume 4.1.1 on the Mac.

Carry-forward observations from the aborted run:
- soundfile can't probe the m4a container ("Format not recognised" warning, defaults 16-bit) —
  consider yt-dlp extracting to mp3/wav instead of m4a.
- The consolidator (raw shapes vs schema.md §2) has still **never seen real module output** — expect
  the real bugs there once a run completes.

## Running it (dev)

```bash
engine/.venv/bin/claudes-ears-serve            # sidecar, 127.0.0.1:8765 (--reload, --port available)
cd desktop && pnpm dev                          # renderer; proxies API same-origin
```
User runs servers themselves — hand over commands, never start them.

## Gotchas (carry forward)

- **Use `engine/.venv/bin/<tool>`, not `uv run`** (strips the ml extra / lock contention).
  `uv pip install -e . --python .venv/bin/python` is fine for re-registering entry points.
- **Stop hook** (`.claude/hooks/verify.sh`) fires on every stop — during parallel agent work it
  snapshots mid-edit trees and reports transient failures; verify at the gate, don't chase each one.
- Index-only tracks (hydrated from DuckDB, not analyzed this session) open a `TrackSummaryPane`,
  not the full workspace — blocked on 4.4.2 (`GET /library/{id}` perception endpoint).
- Dead root `full_perception.py` / `run_demucs.py` — 4.1.5 deletes them (still pending).
- **Deferred:** adversarial `code-review-engineer` pass over Windows 2+ — mandatory before merging
  to `origin/main` (no PR gate anymore).

## Next actions, in order

1. **4.1.7** — MacBook Pro + MPS bring-up; document macOS setup; re-run 4.1.1 there.
2. **4.1.1 finish** — first full `PerceptionDocument` from a real track; fix consolidator mismatches.
3. Unblocked meanwhile on this box: 4.1.5 (delete dead root scripts), 4.3.1 (doc reconcile),
   4.4.2 (track CRUD + detail endpoint), 4.4.4 (data-dir resolution).
