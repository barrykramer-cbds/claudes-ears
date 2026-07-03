# Claude's Ears — Design System

> Cold studio, dark only. Linear-derived surface language, our own subject. The interface holds the
> product's tension — **measurement vs meaning** — and spends color rarely, earning it with data.
> Source of truth for tokens: `tokens.css`. Live reference: `palette.html` → `preview.png`.

## Principles

1. **Color is rare and precise.** The UI is grayscale on near-black; saturated hue only marks data, state, or a voice. A screen with color everywhere is wrong.
2. **The voice taxonomy is the visual vocabulary.** The six relationship colors mean the same thing in every view — legend, ribbon, beeswarm, badge, story.
3. **Quiet chrome, loud data.** Cards, tabs, labels recede; the analysis is the only thing that should catch the eye.
4. **Measurement is mono, meaning is serif.** Numbers/chords/Hz are JetBrains Mono; the story reading is Fraunces italic; everything else is Inter.
5. **One signature.** The beeswarm/ribbon of voices across the song is the thing the app is remembered by. Keep everything around it disciplined.

---

## Color

### Surfaces — cold near-black ramp
| Token | Hex | Use |
|---|---|---|
| `bg` | `#08090A` | app canvas |
| `surface` | `#0F1011` | floating panels / cards |
| `surface-raised` | `#141516` | raised within a panel |
| `surface-input` | `#1C1C1F` | inputs, wells |
| `surface-hover` | `#232326` | hover fill |

### Borders & ink
| Token | Hex | Use |
|---|---|---|
| `border` / `border-strong` | `#23252A` / `#34343A` | hairlines, control edges |
| `line` | `#37393A` | section dividers |
| `edge` / `edge-strong` | `white /.05` / `/.08` | card top-edge highlight, dividers over color |
| `fg` / `fg-secondary` | `#F7F8F8` / `#D0D6E0` | primary / emphasis text |
| `muted` / `faint` | `#8A8F98` / `#62666D` | labels / captions |

### Brand & status
| Token | Hex | Use |
|---|---|---|
| `accent` / `accent-hover` | `#5E6AD2` / `#6E79E6` | primary action, focus, brand |
| `accent-link` | `#828FFF` | links, mono eyebrows |
| `done` `active` `failed` `skipped` | `#27A644` `#5E6AD2` `#EB5757` `#62666D` | pipeline step states |

### The Voice Taxonomy — signature palette
| State | Hex | Meaning |
|---|---|---|
| **solo** | `#FC7840` | one voice owns the stage |
| **support** | `#27A644` | holds underneath |
| **dialogue** | `#5E6AD2` | two voices in exchange |
| **opposition** | `#EB5757` | voices pulling apart |
| **merge** | `#00B8CC` | blending into one |
| **withdraw** | `#8A8F98` | a voice stepping back |

Never recolor these per view. Dots glow via `box-shadow: 0 0 Npx currentColor` at low blur.

### Categorical data hues
`blue #4EA7FC · teal #00B8CC · green #27A644 · orange #FC7840 · red #EB5757 · yellow #F0BF00 · indigo #5E6AD2 · slate #8A8F98` — for stems, spectra, charts. Prefer the voice tokens where a mark *is* a voice.

---

## Elevation, radius, motion

- **Shadows:** `low 0 2px 4px /.10` · `med 0 4px 24px /.20` · `high 0 7px 32px /.35`. Cards use `med` + the inset top-edge highlight.
- **Radii:** button `8px` · card `12px` · panel `16px` · pill `9999px`.
- **Motion (Emil):** enters use `--ease-out` (`cubic-bezier(.23,1,.32,1)`), 140–220ms. The scrubber + tab indicator use `--ease-spring`. Respect `prefers-reduced-motion`. No decorative animation — motion clarifies state, never decorates.

---

## Typography

| Role | Face | Setting | Use |
|---|---|---|---|
| Display / UI | **Inter** | 600, tracking `-0.03em` | titles, tab labels, headings |
| Body | **Inter** | 400–500, `-0.011em` | descriptions, running text |
| Data | **JetBrains Mono** | 400–600, tracking 0 | chords, Hz, bpm, timecodes, counts, axis labels |
| Story | **Fraunces italic** | 400–500 | the grounded reading, pull-quotes — *sparingly* |
| Eyebrow | JetBrains Mono | 11px, `0.16em`, uppercase, `accent-link` | section kickers |

Scale (px): `11 · 12 · 13 · 14(base) · 16 · 18 · 22 · 32 · 44`. Line-height 1.6 body, 1.06 display.

---

## Components

### Card
`.card` = `surface` + `1px border` + inset top-edge highlight (`edge-strong`) + `shadow-med`, radius 12. The whole UI is cards on `bg`.

### Button
| Variant | Fill | Border | Text |
|---|---|---|---|
| primary | `accent` (+inset white /.17) → hover `accent-hover` | — | `#fff` |
| secondary | `surface-hover` | `border-strong` → hover `faint` | `fg` |
| ghost | transparent → hover `surface-raised` | — | `muted` → `fg` |
sizes: md `8×15px` / sm `5×11px`, radius 8, weight 500, tracking `-0.01em`.

### Badge (status pill)
pill, `surface-raised` bg, `border`, `muted` text, 7px leading dot in the relevant hue. e.g. `● Solo dominant`, `● Argues with itself` (red), `● Human · 0.72` (green).

### Tab bar
horizontal, mono-ish labels, active tab = `fg` text + a 2px `accent` underline that springs between tabs; inactive = `muted`. Keyboard: `←/→` or `1–7`.

### Time scrubber
full-width thin track under the header; a 1px `accent` playhead. Hovering any time-aligned view shows a shared vertical guide at the same x.

### Stat readout
mono grid of `k`(label, `faint` uppercase) over `v`(value, `fg`), divided by `border` hairlines. Units in `muted`.

### Beeswarm / ribbon (the signature)
voice-relationship moments as dots (one column per state) or a horizontal ribbon over the time axis. Dots glow; faint step-line marks each cluster's center. This is the headline of the Voices tab.

---

## Information architecture — the app shell

The app is a **persistent shell**: a **Library sidebar** (the analyzed tracks) on the left, a **workspace**
on the right (the selected track's tabbed analysis). This frame is always present — launch never drops
the user onto a bare card. Time is the workspace's shared spine: Voices / Harmony / Structure / Emotion
align to the same x-axis.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ◐ Claude's Ears                        ⌘K search             [ + Add ]    │ titlebar
├───────────────┬──────────────────────────────────────────────────────────┤
│  LIBRARY      │  The Weight · studio                A · 71 bpm · 3:48     │ track header
│  ───────────  │  ├──────────────── scrubber ▎ ─────────────────────────┤  │
│ ▸ The Weight  │  Voices  Harmony  Structure  Space  AI  Story  Library    │ tabs
│   Tokyo Live  │  ▔▔▔▔▔▔                                                    │
│   Ghost Note  │                                                           │
│   …           │              « selected track · active tab »              │
│  ───────────  │                                                           │
│  + Add track  │                                                           │
└───────────────┴──────────────────────────────────────────────────────────┘
```

**Library sidebar:** the analyzed tracks (DuckDB), newest first; selecting one loads its workspace.
`+ Add` opens the file picker → analysis. Collapsible; `⌘K` searches the library. The sidebar is the
home for cross-track features (sonic twins, version compare) that the single-track tabs can't hold.

| Tab | Schema source | Shows |
|---|---|---|
| **Voices** | `vocals.relationships` (`story[]`, `distribution`, `register`, `breath`) | the beeswarm/ribbon — the headline |
| **Harmony** | `harmony.chords`, roman, modulations, `harmonic_rhythm` | chord ribbon on the time axis + key/cadence reading |
| **Structure** | `structure` sections + `emotion` trajectory | section bands + valence/arousal curve, same axis |
| **Space** | `spatial` stereo field + `depth` | width/balance + room/distance placement |
| **AI lens** | `ai_detection` | "argues vs agrees with itself" — a lens, not a verdict |
| **Story** | `story.story_moments[]` | grounded reading, each moment anchored to chord/emotion/relationship |
| **Library** | DuckDB + twins | track browser + sonic twins (lights up when backend is wired) |

### Voices tab (headline)
```
┌─ Vocal relationship · density over time ───────────────── 03:48 ─┐
│   · ·        ·· ·                                                 │
│  ···· ·   ·· ···· ·    ·· ·       ··· ·       ·· ··               │   beeswarm,
│ ·······  ········· · ········  ·· ·· ·    ·········  · ··· ·      │   one column
│  ····· ·   ··· ··    · ·· ·       · ·        ·· ··                │   per state
│   Solo     Support   Dialogue   Opposition   Merge   Withdraw    │
└──────────────────────────────────────────────────────────────────┘
┌─ distribution ─────────────┐  ┌─ register · breath ──────────────┐
│ Solo ████████░░ 0.50       │  │ pitch 196.4Hz  breath 0.34       │
│ Support █████░░░ 0.30      │  │ range 14.0 st  voiced 0.62       │
│ Dialogue ███░░░░ 0.20     │  └──────────────────────────────────┘
└────────────────────────────┘
   "One voice carries the weight alone — until the bridge…"   ← Fraunces
```

### First launch — empty library (same shell, drop target in the main pane)
```
┌──────────────────────────────────────────────────────────────────────────┐
│ ◐ Claude's Ears                                              [ + Add ]    │
├───────────────┬──────────────────────────────────────────────────────────┤
│  LIBRARY      │                                                           │
│  ───────────  │              ◐  Drop a song in to hear it                 │
│  No tracks    │            FLAC · WAV · MP3 — analyzed locally            │
│  yet          │                  [ Choose a file ]                        │
│  ───────────  │                                                           │
│  + Add track  │                                                           │
└───────────────┴──────────────────────────────────────────────────────────┘
```

### Analyzing — runs inline in the main pane; the track is already in the sidebar
```
┌───────────────┬──────────────────────────────────────────────────────────┐
│  LIBRARY      │  The Weight · studio                          analyzing   │
│  ───────────  │  ▸ separation              ✓                              │
│ ◐ The Weight  │  ▸ stem analysis           ✓                              │
│   …           │  ▸ vocal relationships     ◐ running                      │
│               │  ▸ harmony                 ·                              │
│  + Add track  │  6 / 21                                                   │
└───────────────┴──────────────────────────────────────────────────────────┘
```

---

## Launch & data flow (production — no mock)

The shipped app talks to the real **FastAPI sidecar**; mock data is dev-only (`VITE_USE_MOCK`, off in
builds). On launch:

1. **Electron main spawns the sidecar** (packaged Python, see `tech-stack.md`), waits for health, and
   injects its real port as `VITE_API_BASE_URL` into the renderer.
2. Renderer loads the **Library** from `GET /library` (DuckDB). Empty → first-launch drop state above;
   non-empty → select the most-recent track and show its workspace.
3. **Add a track** → file picker (`window.electron.openAudioFile`) → `POST /jobs` → SSE `/.../events`
   drives the inline step list. One job at a time (single GPU worker); a second add queues.
4. On complete → the track joins the sidebar and its workspace opens on **Voices**.

## User flows

1. **Analyze** — `+ Add` → pick a real audio file → job runs inline → lands on Voices.
2. **Read** — tab between lenses; the scrubber position carries across time-aligned tabs. `Story` synthesizes the reading from the other lenses.
3. **Browse / twins** — the sidebar lists analyzed tracks; selecting one loads its workspace; the Library tab surfaces its sonic twins (DuckDB VSS), nearest-first.
4. **Compare** — pick a second version → `version_compare` → producer-fingerprint deltas (a focused view off the sidebar, not a per-track tab).

---

## States (every data view designs all four)

| State | Treatment |
|---|---|
| **empty** | one quiet line + the action that fills it (no illustration). "Drop a track to listen." |
| **loading** | skeleton at the real layout's shape; mono `running` ticks for pipeline steps. |
| **error** | what failed + how to fix, in the interface's voice; `failed` red dot. Never an apology. |
| **ideal** | the composed view above. |

Personal tool: no onboarding, no marketing empties. Density over breathing room. Keyboard-first.
