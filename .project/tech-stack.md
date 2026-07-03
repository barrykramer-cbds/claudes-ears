# Claude's Ears — Tech Stack

> Two parts: the **existing pipeline** (Python CLI modules, documented below) and the
> **planned application layer** (local frontend + backend) we're designing now. The
> application-layer section is a living document — decided items are recorded, open
> questions are listed. See `prd.md` for the product framing.

## Language & Runtime

- **Python** — primary language, all pipeline modules
- **GPU recommended** for demucs stem separation; Whisper runs with `fp16=False` on some NVIDIA cards

---

## Application Layer (planned, in progress)

> Deployment model: **single-user local tool, not hosted.** No queue, auth, server DB,
> or autoscaling. This constraint drives every choice below.

### Decided

| Concern | Choice | Rationale |
|---|---|---|
| **Delivery** | Desktop app (cross-platform Mac + Windows) | Personal local tool — native install beats "run a localhost server"; Barry is on both OSes |
| **Desktop shell** | **Electron** (Chromium + Node main process) | ML payload (1.5–3 GB) dwarfs Chromium's overhead so its only real downside doesn't bite; identical rendering on both OSes (matters for animation polish); mature Python-sidecar recipes; Node main matches the JS frontend |
| **Backend** | FastAPI, run as a **Python sidecar** spawned + managed by the Electron main process (localhost HTTP + SSE) | Async-native, SSE built in, Pydantic gives typed contracts at every boundary (also fixes the hard-indexed-JSON bug class) |
| **Job execution** | In-memory job registry + per-job working dir; single GPU worker (jobs serialize) | Personal tool — transient job state needs no persistence; one GPU naturally serializes |
| **Progress** | Server-Sent Events (SSE) | One-directional server→client; simpler than WebSocket, exact fit |
| **Pipeline integration** | **In-process imports** — each module refactored to an importable `analyze(path) -> dict`, called by the backend in one warm process. Done incrementally, heaviest modules first; each keeps a thin CLI shim | Loads demucs/whisper **once** (multi-minute speedup); clean under PyInstaller (no spawning a frozen binary); removes the shell-injection root (`ISSUE-001`); matches `python.md` (CLI separate from library). Not a rewrite — a refactor + reorganize of existing code |
| **Consolidation** | `PerceptionDocument` (Pydantic) → one `perception.json` per track | The missing keystone — merges ~20 scattered JSONs into one typed, renderable artifact |
| **Local DB** | **DuckDB** (embedded, single file, no server) | Queries the per-track `perception.json` in place (zero ETL); materialized track table for the library/genome view; VSS extension for "sonic twins" similarity over genome vectors |
| **Twin-search (VSS)** | v1 feature — DuckDB VSS over genome vectors | The distinctive "find sonic twins" library view ships in v1, not deferred |
| **Dependencies** | `uv` + `pyproject.toml` + `uv.lock`, target **Python 3.12** | Lock file = reproducible Mac/Win builds (critical once PyInstaller-frozen); fast resolution of the heavy ML tree. Migration is additive — `requirements.txt` keeps working. (Today: plain pip + `requirements.txt`, unpinned) |
| **Report delivery** | In-app only (v1) | Render the `PerceptionDocument` in the UI; standalone HTML export deferred |
| **Frontend** | React + Vite + TypeScript + Tailwind + shadcn/ui, rendered in the Electron webview | `react-engineer` stack; **native file dialogs / drag-drop replace upload** (file is already on disk); SSE progress; renders the `PerceptionDocument` |
| **Packaging** | PyInstaller-frozen Python sidecar + Electron Builder; code-sign + notarize (Mac), sign (Win) | The real engineering cost of "desktop" — freeze torch/demucs/whisper cross-platform (`devops-engineer` turf) |
| **Model weights** | **Bundled in the installer** — whisper `base` (~145 MB) + demucs `htdemucs` (~80 MB) ≈ 225 MB | Small next to the torch/CUDA payload (1.5–3 GB) you ship regardless; works offline on install, deterministic (reproducible analysis), no rotting-download-URL risk |
| **Interaction polish** | Emil Kowalski doctrine (`emil-design-eng` skill) | Motion/transitions/gesture polish so the output "feels right" |

### Open / to discuss

_All major architecture decisions resolved. Remaining pre-build task: finalize the `PerceptionDocument`
leaf fields against real module outputs (map each module's actual JSON shape) — a build-plan task, not an open decision._

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `librosa>=0.10.0` | Core audio feature extraction (chroma, MFCC, tempo, beats, spectral) |
| `soundfile>=0.12.0` | Audio I/O |
| `numpy>=1.24.0` | Numerical computation |
| `scipy>=1.10.0` | Signal processing |
| `demucs>=4.0.0` | GPU stem separation (vocals/drums/bass/other) via htdemucs |
| `scikit-learn>=1.3.0` | ML utilities (NMF, clustering, etc.) |
| `torch>=2.0.0` | PyTorch — demucs and Whisper backend |
| `torchaudio>=2.0.0` | Audio loading for torch models |
| `openai-whisper>=20230918` | Speech recognition for lyric transcription |
| `vaderSentiment>=3.3.2` | Sentiment scoring for emotional trajectory |
| `requests>=2.28.0` | Lyrics fetching from external sources |
| `yt-dlp>=2024.0.0` | Audio downloading |
| `ffmpeg-python>=0.2.0` | Media processing wrapper (ffmpeg must be on PATH) |

---

## Architecture Pattern — today (flat scripts)

Flat module layout at repo root. Each module is a standalone CLI script that produces a sibling JSON. `full_perception.py` orchestrates by spawning 21 subprocesses. This is what we're refactoring *from*.

---

## Project Structure — target (desktop app)

Two halves: a **Python package** (`src/`) holding the pipeline, API, DB, and schemas; and a **`desktop/`** Node project holding the Electron shell + React renderer. The 24 analysis modules move into `src/claudes_ears/analysis/` and become importable `analyze()` functions (the refactor) while keeping thin CLI shims.

```
claudes-ears/
├── pyproject.toml                 # uv project: deps + ruff/mypy/pytest config
├── uv.lock                        # locked deps → reproducible Mac/Win builds
├── src/
│   └── claudes_ears/
│       ├── analysis/              # the 24 modules, refactored to analyze(path) -> dict
│       │   ├── vocal_relationships.py
│       │   ├── chord_progression.py
│       │   ├── music_theory.py
│       │   ├── ... (all 24)
│       │   └── ai_detector.py
│       ├── separation/            # demucs wrapper (was run_demucs.py)
│       ├── pipeline/
│       │   ├── orchestrator.py    # replaces full_perception.py — calls analyze() in phase order
│       │   ├── steps.py           # phase/step registry (name, fn, optional, deps)
│       │   └── consolidator.py    # merges module outputs → PerceptionDocument
│       ├── models/                # Pydantic schemas (the contracts)
│       │   ├── perception.py      # PerceptionDocument + sub-models
│       │   └── jobs.py            # Job, JobStatus, ProgressEvent
│       ├── db/                    # DuckDB layer
│       │   ├── library.py         # track-index upsert + queries
│       │   ├── twins.py           # VSS similarity over genome vectors
│       │   └── schema.sql
│       ├── api/                   # FastAPI sidecar
│       │   ├── app.py             # instance + lifespan (warm demucs/whisper once)
│       │   ├── routes/{jobs,library}.py
│       │   └── sse.py             # progress event stream
│       └── cli.py                 # standalone CLI entry points (the shims)
├── tests/                         # pytest — mirrors src/ layout
├── desktop/                       # Electron + React (Node half)
│   ├── package.json
│   ├── electron/
│   │   ├── main.ts                # spawns + manages the Python sidecar; native file dialogs
│   │   └── preload.ts             # safe IPC bridge to the renderer
│   └── renderer/                  # React + Vite + Tailwind + shadcn
│       ├── index.html
│       ├── vite.config.ts
│       └── src/
│           ├── App.tsx
│           ├── components/
│           └── lib/api.ts         # typed client + SSE (mirrors Pydantic schemas via Zod)
├── .project/                      # project documentation
└── .claude/                       # rules, agents, hooks
```

**Boundaries:** `analysis/` modules never import from `api/` or `db/` (pure analysis, testable in isolation). `pipeline/` composes `analysis/`. `api/` depends on `pipeline/` + `db/` + `models/`. The Electron main process is the only thing that knows the sidecar exists; the renderer only talks HTTP/SSE to localhost.

---

## Schemas

> The `PerceptionDocument` is the central contract: the consolidator builds it, the API serves it,
> the renderer displays it, DuckDB indexes it. Structure below is the **target shape grouped by
> analysis domain**; exact leaf fields are finalized against real module outputs during the
> consolidator build (a build-plan task). Pydantic v2 models in `src/claudes_ears/models/`.

### PerceptionDocument (per track)

```
PerceptionDocument
├── schema_version: str                 # bump when the contract changes
├── track: TrackMeta                    # id, title, artist, source_path, duration_s,
│                                        #   sample_rate, analyzed_at, pipeline_version
├── separation: SeparationInfo          # model, stems_present[], stem_dir
├── vocals: VocalAnalysis
│   ├── relationships: list[RelationshipSegment]   # start, end, label
│   │        # label ∈ solo|support|dialogue|opposition|merge|withdraw, confidence
│   ├── layers | intervals | narrative | register | breath
├── rhythm: RhythmAnalysis              # groove_timing, tempo, harmonic_rhythm
├── harmony: HarmonyAnalysis
│   ├── chords: list[ChordSpan]         # start, end, symbol, roman
│   ├── key, mode, cadences[]           # music_theory
├── timbre: TimbreAnalysis              # timbral_decomposition (NMF), freq_interaction
├── spatial: SpatialAnalysis            # stereo_field, depth_reverb
├── structure: list[Section]            # temporal_segmentation (label, start, end)
├── emotion: EmotionTrajectory          # valence/arousal series + summary
├── lyrics: LyricsAnalysis | None       # transcript, semantic_lyrics (optional)
├── story: StoryReading | None          # the grounded narrative reading (optional)
├── ai_detection: AiDetection           # verdict, self_opposition_score, confidence
└── genome: GenomeVector                # fixed-length feature vector → DuckDB VSS
```

Every optional sub-model is `| None` so a degraded/failed step yields `null`, **not** a missing
key or an `{"error": ...}` blob — this is the typed fix for the hard-indexed-contract bug class
(`ISSUE-008`). Consolidator validates once; everything downstream trusts the model.

### DuckDB schema (library index + twins)

Derived cache over the per-track JSON — rebuildable from `perception.json` files at any time.

```sql
-- one row per analyzed track; summary fields for fast library filtering
CREATE TABLE tracks (
  track_id         TEXT PRIMARY KEY,
  title            TEXT,
  artist           TEXT,
  source_path      TEXT,
  duration_s       DOUBLE,
  key              TEXT,
  mode             TEXT,
  tempo            DOUBLE,
  valence          DOUBLE,      -- emotion summary
  arousal          DOUBLE,
  ai_verdict       TEXT,
  ai_score         DOUBLE,
  pipeline_version TEXT,
  analyzed_at      TIMESTAMP,
  perception_path  TEXT         -- pointer to the full PerceptionDocument JSON
);

-- genome feature vectors for "sonic twins" similarity search
CREATE TABLE genome_vectors (
  track_id  TEXT PRIMARY KEY,
  vector    FLOAT[]            -- fixed dimension N (set when genome features are finalized)
);
-- VSS (HNSW) index on genome_vectors.vector → nearest-neighbour twin lookup
```

`tracks` is upserted by `track_id` on every (re)analysis — idempotent, no duplicate rows.

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `CLAUDES_EARS_STEMS` | `./stems/htdemucs` | demucs stem output root |
| `CLAUDES_EARS_MUSIC` | `./music` | source audio library (batch mode) |

---

## Tooling

| Tool | Purpose |
|------|---------|
| `ruff` | Linting and formatting |
| `mypy` | Type checking |
| `ffmpeg` | Must be on PATH — used by librosa, demucs, yt-dlp |

---

## Install

```bash
git clone https://github.com/barrykramer-cbds/claudes-ears.git
cd claudes-ears
pip install -r requirements.txt
# ffmpeg must be on PATH
```

---

*Last updated: 2026-06-30*
