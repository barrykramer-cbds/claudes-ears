"""Raw module dicts -> one validated PerceptionDocument (schema.md §2/§3/§5).

Single validation boundary (ISSUE-008/012): a degraded/missing step nulls its
domain — never a raise, a missing key, or an ``{"error":...}`` blob downstream.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, cast

from claudes_ears._sanitize import sanitize
from claudes_ears.models.perception import SCHEMA_VERSION, PerceptionDocument, TrackMeta

if TYPE_CHECKING:
    from collections.abc import Mapping

RawDict = dict[str, object]

#: genome dim -> nested path into the analyze_stems dict (schema §3).
_GENOME_PATHS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("vocal_pitch", ("vocals", "pitch_mean_hz")),
    ("vocal_range", ("vocals", "pitch_range_semitones")),
    ("vocal_entropy", ("vocals", "vocal_melodic_entropy")),
    ("vocal_breathiness", ("vocals", "breathiness")),
    ("vocal_presence", ("vocals", "voiced_fraction")),
    ("drum_tempo", ("drums", "tempo_bpm")),
    ("drum_regularity", ("drums", "beat_regularity")),
    ("drum_density", ("drums", "onsets_per_second")),
    ("drum_kick_pct", ("drums", "kit_balance", "kick")),
    ("bass_movement", ("bass", "root_movement_rate")),
    ("texture_centroid", ("other", "centroid_hz")),
    ("texture_harmonic", ("other", "harmonic_pct")),
)


def consolidate(
    track: TrackMeta,
    results: Mapping[str, Mapping[str, object] | None],
) -> PerceptionDocument:
    """Map per-step raw outputs to a validated PerceptionDocument (validates once)."""
    raw: RawDict = {
        "schema_version": SCHEMA_VERSION,
        "track": track.model_dump(by_alias=True),
        "separation": _clean(results.get("separation")),
        "stems": _clean(results.get("analyze_stems")),
        "vocals": _vocals(results),
        "rhythm": _domain({"groove": _clean(results.get("groove_timing"))}),
        "harmony": _harmony(results),
        "timbre": _domain(
            {
                "decomposition": _clean(results.get("timbral_decomposition")),
                "interaction": _clean(results.get("freq_interaction")),
            }
        ),
        "spatial": _domain(
            {
                "stereo": _clean(results.get("stereo_field")),
                "depth": _clean(results.get("depth_reverb")),
            }
        ),
        "structure": _structure(results.get("temporal_segmentation")),
        "emotion": _emotion(results.get("emotional_trajectory")),
        "lyrics": _clean(results.get("semantic_lyrics")),
        "story": _clean(results.get("story_reader")),
        "ai_detection": _clean(results.get("ai_detector")),
        "genome": _genome(results.get("analyze_stems")),
    }
    return PerceptionDocument.model_validate(raw)


def _clean(raw: Mapping[str, object] | None) -> RawDict | None:
    """Sanitize a raw step dict (non-finite floats -> None); missing step -> None."""
    if raw is None:
        return None
    return cast("RawDict", sanitize(dict(raw)))


def _domain(subfields: dict[str, RawDict | None]) -> dict[str, RawDict | None] | None:
    """Null a multi-module domain only when every constituent step degraded."""
    return subfields if any(value is not None for value in subfields.values()) else None


def _vocals(results: Mapping[str, Mapping[str, object] | None]) -> dict[str, RawDict | None] | None:
    return _domain(
        {
            "layers": _clean(results.get("vocal_layers")),
            "intervals": _clean(results.get("vocal_intervals")),
            "narrative": _clean(results.get("vocal_narrative")),
            "relationships": _clean(results.get("vocal_relationships")),
            "register": _clean(results.get("register_tracking")),
            "breath": _clean(results.get("breath_detection")),
        }
    )


def _harmony(
    results: Mapping[str, Mapping[str, object] | None],
) -> dict[str, RawDict | None] | None:
    return _domain(
        {
            "chords": _clean(results.get("chord_progression")),
            "harmonic_rhythm": _harmonic_rhythm(results.get("harmonic_rhythm")),
            "theory": _music_theory(results.get("music_theory")),
        }
    )


def _harmonic_rhythm(raw: Mapping[str, object] | None) -> RawDict | None:
    """Normalize the degenerate branch's ``harmonic_rhythm_windows`` to ``windows``."""
    cleaned = _clean(raw)
    if cleaned is None:
        return cleaned
    if "windows" not in cleaned and "harmonic_rhythm_windows" in cleaned:
        cleaned["windows"] = cleaned["harmonic_rhythm_windows"]
    return cleaned


def _music_theory(raw: Mapping[str, object] | None) -> RawDict | None:
    """Sort ``unique_numerals`` — the source builds it from an unordered set (§5)."""
    cleaned = _clean(raw)
    if cleaned is None:
        return cleaned
    numerals = cleaned.get("unique_numerals")
    if isinstance(numerals, list):
        cleaned["unique_numerals"] = sorted(str(item) for item in numerals)
    return cleaned


def _structure(raw: Mapping[str, object] | None) -> RawDict | None:
    """Collapse an empty ``narrative`` ({} at the source) to None."""
    cleaned = _clean(raw)
    if cleaned is None:
        return cleaned
    if cleaned.get("narrative") == {}:
        cleaned["narrative"] = None
    return cleaned


def _emotion(raw: Mapping[str, object] | None) -> RawDict | None:
    """Collapse the ``{error}`` variant to a null domain (ISSUE-008)."""
    cleaned = _clean(raw)
    if cleaned is None or "error" in cleaned:
        return None
    return cleaned


def _genome(raw: Mapping[str, object] | None) -> RawDict | None:
    """Extract the 12-dim vector from analyze_stems; all-or-nothing on finiteness."""
    cleaned = _clean(raw)
    if cleaned is None:
        return None
    vector: RawDict = {}
    for dim, path in _GENOME_PATHS:
        value = _dig(cleaned, path)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if not math.isfinite(value):
            return None
        vector[dim] = float(value)
    return vector


def _dig(data: RawDict, path: tuple[str, ...]) -> object:
    """Walk a nested-dict path, returning None on any missing or non-dict node."""
    node: object = data
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node
