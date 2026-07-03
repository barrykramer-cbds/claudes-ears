# Claude's Ears

An audio perception pipeline that **listens** to music rather than merely measuring it.

Most music-analysis tooling stops at feature extraction — chroma, MFCC, tempo, key, beats. Claude's Ears uses that layer as a substrate (via `librosa` and `demucs`) and builds an interpretive layer on top: it asks what the voices are *saying to each other*, what a producer *did* to an arrangement, and what *story* a song carries.

It began from one question — "can you hear music?" — and grew into a ~25-module engine for vocal-relationship analysis, producer-fingerprint detection, cross-track acoustic mapping, and lyric-aligned story reading.

## What makes it different

The music-information-retrieval ecosystem already does measurement and source separation well, and a mature industry already does forensic AI-music detection (artifact/watermark classifiers). Claude's Ears deliberately occupies the space none of those touch:

- **Vocal relationships, not just vocal features.** A taxonomy of how simultaneous voices relate moment to moment — `solo / support / dialogue / opposition / merge / withdraw` — instead of a single "vocals" blob. (`vocal_relationships.py`)
- **The producer's fingerprint.** Given a studio and a live version of the same song, the pipeline quantifies the delta across every dimension. That delta *is* the producer's invisible hand — what was added, buried, or imposed on the performer. (`version_compare.py`)
- **Architectural AI detection.** Rather than hunting spectral artifacts or watermarks, it asks a structural question: does the voice *argue with itself* (self-opposition, characteristic of human performance) or *agree with itself* (self-reinforcement, characteristic of generated vocals)? (`ai_detector.py`)
- **Grounded story reading.** Academic LLM-music work generally assumes a model "cannot hear" and reads lyrics/metadata as a text proxy. This pipeline inverts that: it feeds measured acoustic data (vocal relationships, harmonic function, emotional trajectory) into a lyric-aligned reading. (`story_reader.py`)

### An honest limitation

The architectural AI detector is **not** a forensic discriminator and does not try to be. At the top end of studio production, heavily-produced human pop and AI-generated music converge on the same commercial polish, and post-production (EQ, compression, reverb, layering) smooths away the very signals detectors rely on — a ceiling the broader detection industry has independently documented. The detector here characterizes vocal *personality and architecture*; it is a lens, not a verdict.

## Architecture

```
Audio file
  │
  ├─ Phase 1  Separation        run_demucs.py  (GPU stem split: vocals/drums/bass/other)
  │
  ├─ Phase 2  Stem analysis     analyze_stems · vocal_layers · vocal_intervals ·
  │                             groove_timing · freq_interaction ·
  │                             timbral_decomposition · vocal_narrative · vocal_relationships
  │
  ├─ Phase 2c/2d Vocal          register_tracking (chest/head/falsetto/fry) ·
  │                             breath_detection (physical presence)
  │
  ├─ Phase 3  Full mix          stereo_field · temporal_segmentation ·
  │                             depth_reverb · chord_progression
  │
  ├─ Phase 4  Derived           emotional_trajectory · semantic_lyrics ·
  │                             story_reader · harmonic_rhythm · music_theory
  │
  └─ Phase 5  Library           genome_map (cross-track DNA) · temporal_genome (cross-era twins)

Orchestration: full_perception.py   ·   Comparison tool: version_compare.py
```

## Install

```bash
git clone https://github.com/barrykramer-cbds/claudes-ears.git
cd claudes-ears

# Engine (Python 3.12, uv)
cd engine && uv sync --extra ml && cd ..

# Desktop app (pnpm)
cd desktop && pnpm install && cd ..
# ffmpeg must be on PATH (used by librosa, separation, yt-dlp)
```

A GPU is strongly recommended for stem separation — CPU works but takes minutes per track.

## Running it

Two processes, two terminals, from the repo root:

```bash
# 1. Engine (FastAPI sidecar on 127.0.0.1:8765)
engine/.venv/bin/claudes-ears-serve            # add --reload for dev

# 2. Frontend (vite dev server; proxies API calls to the sidecar)
cd desktop && pnpm dev
```

Open the printed vite URL, hit **Add** and drop in a YouTube URL or a local audio file — the full
pipeline runs with live per-step progress, and finished tracks land in the library dashboard.

Paths are configurable via environment variables (defaults are relative to the engine dir):

| Variable | Default | Purpose |
|---|---|---|
| `CLAUDES_EARS_STEMS` | `./stems/htdemucs` | stem separation output root |
| `CLAUDES_EARS_MUSIC` | `./music` | source audio library (YouTube downloads land here) |

Single pipeline steps can also run headless: `engine/.venv/bin/claudes-ears <step> <path>`.

## Design principles

1. The music is the vessel; the story is what it carries. Never prioritize measurement over meaning.
2. A solo is a vocal spotlight — the performer's personality demanding the stage. Expression, not vulnerability.
3. Measurement is not listening. Numbers describe what happened; listening hears why.
4. The arrangement is a negotiation between performer and producer. The recording freezes the outcome.
5. Personality drives architecture.

## License

[MIT](LICENSE) — Barry Kramer, 2026. Built collaboratively, human and AI.
