# Session Handoff — 2026-07-03 (Audit complete → Phase 4 next)

> Read this first. **Direction now: start Phase 4 prod wiring**, beginning with a real audio run to
> flush out bugs. Polish fixes landed; a full-stack audit reset our understanding of what's real.

## Where we are

- **Committed + pushed** on `origin/feat/desktop-app` (origin = Barry's repo; see "After Phase 4"):
  - `51e508e` — G2 (engine/ + desktop/ restructure, dep modernization, demucs→audio-separator).
  - `a1ab948` — Window 2: 12 derived module ports + FastAPI sidecar + db metadata/twins + full desktop
    workspace. All suites green.
- Polish fixes **committed** as `818f169` (gate green: eslint + tsc + vitest 24 passed): `randomId()`
  v4 fallback fixing the `crypto.randomUUID` upload crash; DropZone deleted for a quiet empty state.
- Untracked screenshots (`app-entry.png`, `app-workspace.png`) remain unstaged.

## The audit (this session's main event)

Ran 4 parallel readers over backend / DuckDB / frontend / pipeline. **Full writeup: `build-plan.md` →
"Audit Snapshot — 2026-06-30".** One-line verdict: **the backend is real and green; the frontend is
dormant behind the mock flag.**

- Real & unit-tested (but **never run on real audio**): orchestrator (21 steps, in-process), real SSE,
  live DuckDB persistence, HNSW twin search. Endpoints: `POST /jobs`, job status/perception/events(SSE),
  `GET /library`, `/library/{id}/twins`.
- Dormant: `lib/api.ts` real client is gated by `VITE_USE_MOCK` (defaults **true**). The dev "song" is the
  `mock/perception.ts` fixture ("The Weight" by The Band).
- Frontend library is in-memory only (wiped on reload); never calls `GET /library`.
- New gaps → now tracked as **Phase 4.1.6 + 4.4.1–4.4.5** in build-plan: no rename/delete/track-detail,
  jobs in-memory (no list/cancel/persistence), no upload (sidecar-local path only), `library.duckdb`
  CWD-relative, `get_track_metadata→temporal_genome` never invoked at runtime.

## Next action — Phase 4.1.1 (real run), currently BLOCKED

The single highest-value next step: run the orchestrator on **one real vocal track** to surface
raw-shape mismatches vs `schema.md` §2. **Blocked only on an audio file** — none in the repo.

- To unblock: drop a vocal track (multi-voice exercises the most modules) into
  `/home/ul0gic/projects/claudes-ears/music/`, or give an absolute path.
- Runtime is ready: `ffmpeg`, `audio_separator`, `faster_whisper`, orchestrator all import.
  **CPU-only, no GPU** → separation takes minutes/track, not seconds. Be patient on the first run.
- Drive it via `engine/.venv/bin/python` calling `run_track` (NOT the dead root `full_perception.py`,
  NOT the server). The CLI (`python -m claudes_ears <step> <path>`) only runs single steps.

## Gotchas (carry forward)

- **Never start servers.** User runs dev servers themselves — hand over the command.
- **Use `engine/.venv/bin/<tool>`, not `uv run`** (uv run can strip the `ml` extra + lock-contend).
  Shell `cd` doesn't persist between Bash calls — use absolute paths or `cd … && …`.
- **Stop hook** (`.claude/hooks/verify.sh`) is subtree-aware, Stop-only, blocking.
- Dead root `full_perception.py` / `run_demucs.py` — Phase 4.1.5 deletes them.
- **Deferred:** adversarial `code-review-engineer` pass over Window 2 — run before finalizing the PR.

## After Phase 4

Phase 5 hardening, Phase 6 PyInstaller + electron-builder installer + signing. The fork is deleted;
`origin` is now Barry's repo (`barrykramer-cbds/claudes-ears`) with direct push access — work stays on
`feat/desktop-app`, merged straight into `origin/main` when done (no PR gate, so run the deferred
adversarial review first).
