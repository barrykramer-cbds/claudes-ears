"""Semantic lyric reading: VADER surface sentiment + grounded Claude interpretation."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import TYPE_CHECKING, cast
from urllib.parse import quote

import httpx as httpx

from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:
    from collections.abc import Iterable

_LYRICS_API = "https://api.lyrics.ovh/v1"
_ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_LLM_MODEL = "claude-sonnet-4-6"
_LLM_MAX_TOKENS = 1500
_WHISPER_MODEL_SIZE = "base"

_SYSTEM_PROMPT = (
    "You are a lyric analyst. Given song lyrics, return ONLY valid JSON: "
    '{"themes":[],"imagery":[],"cultural_references":[{"reference":"","tradition":"",'
    '"significance":""}],"emotional_arc":"","subtext":"","surface_vs_depth":"",'
    '"semantic_valence":0.0,"key_lines":[{"line":"","significance":""}]} '
    "semantic_valence is -1 to +1 by MEANING not vocabulary: captivity in gentle "
    "language is negative; freedom in dark metaphors is positive."
)


def _parse_artist_title(stem_name: str) -> tuple[str | None, str | None]:
    """Split a canonical 'Artist - Title' stem-directory name; (None, None) if it doesn't match."""
    if " - " in stem_name:
        artist, title = stem_name.split(" - ", 1)
        return artist.strip(), title.strip()
    return None, None


def _fetch_lyrics_web(artist: str, title: str) -> dict[str, object] | None:
    """Look up lyrics on lyrics.ovh; path segments are percent-encoded (ISSUE-009)."""
    url = f"{_LYRICS_API}/{quote(artist, safe='')}/{quote(title, safe='')}"
    try:
        response = httpx.get(url, timeout=10.0)
    except httpx.RequestError:
        return None
    if response.status_code != 200:
        return None
    raw = response.json().get("lyrics", "")
    lines = [line.strip() for line in raw.split("\n") if line.strip()]
    if len(lines) < 2:
        return None
    return {"source": "lyrics.ovh", "text": "\n".join(lines), "lines": lines}


def _load_whisper_model() -> object:
    """Construct a CPU faster-whisper model; isolated so tests patch it without loading weights."""
    from faster_whisper import WhisperModel  # type: ignore[import-untyped]  # no py.typed marker

    return WhisperModel(_WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")


def _transcribe_vocals(vocals: Path) -> dict[str, object] | None:
    """Transcribe the vocals stem with faster-whisper; None if the stem is absent."""
    if not vocals.exists():
        return None
    model = _load_whisper_model()
    segments, _info = cast("tuple[Iterable[object], object]", model.transcribe(str(vocals)))  # type: ignore[attr-defined]
    lines = [text for segment in segments if (text := str(segment.text).strip())]  # type: ignore[attr-defined]
    if not lines:
        return None
    return {"source": "whisper", "text": "\n".join(lines), "lines": lines}


def _vader_sentiment(lines: list[str]) -> dict[str, object]:
    """Per-line + overall VADER compound sentiment; degraded dict if VADER is unavailable."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    except ImportError:
        return {"overall_sentiment": None, "note": "VADER not installed"}

    analyzer = SentimentIntensityAnalyzer()
    sentiments = [
        {
            "text": line,
            "compound": round(analyzer.polarity_scores(line)["compound"], 4),
        }
        for line in lines
    ]
    overall = round(sum(s["compound"] for s in sentiments) / max(len(sentiments), 1), 4)
    return {
        "overall_sentiment": overall,
        "line_sentiments": sentiments[:50],
        "most_positive": max(sentiments, key=lambda s: s["compound"])["text"] if sentiments else "",
        "most_negative": min(sentiments, key=lambda s: s["compound"])["text"] if sentiments else "",
    }


def _semantic_analysis_via_api(lyrics_text: str, api_key: str) -> dict[str, object] | None:
    """Grounded literary reading via the Claude Messages API; None on missing key or any failure."""
    try:
        response = httpx.post(
            _ANTHROPIC_API,
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
            },
            json={
                "model": _LLM_MODEL,
                "max_tokens": _LLM_MAX_TOKENS,
                "system": _SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": f"Analyze these lyrics:\n\n{lyrics_text}"}
                ],
            },
            timeout=30.0,
        )
    except httpx.RequestError:
        return None
    if response.status_code != 200:
        return None
    try:
        text = response.json()["content"][0]["text"].strip()
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        result = cast("dict[str, object]", json.loads(text))
    except (KeyError, IndexError, ValueError):
        return None
    result["method"] = "claude_api"
    return result


def analyze(separation: dict[str, object]) -> dict[str, object]:
    """Read a song's lyrics (web or whisper) and produce VADER + grounded-LLM semantic analysis.

    Optional step: degrades to VADER-only or unavailable rather than raising on any failure.
    """
    stem_dir = Path(str(separation.get("stem_dir", "")))
    artist, title = _parse_artist_title(stem_dir.name)

    lyrics: dict[str, object] | None = None
    if artist and title:
        lyrics = _fetch_lyrics_web(artist, title)
    if lyrics is None:
        lyrics = _transcribe_vocals(stem_dir / "vocals.wav")
    if lyrics is None:
        return cast("dict[str, object]", sanitize({"available": False, "method": "unavailable"}))

    lines = cast("list[str]", lyrics["lines"])
    text = cast("str", lyrics["text"])
    vader = _vader_sentiment(lines)

    semantic: dict[str, object] | None = None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        semantic = _semantic_analysis_via_api(text, api_key)

    result: dict[str, object] = {
        "available": True,
        "source": lyrics["source"],
        "line_count": len(lines),
        "text": text[:3000],
        "vader": vader,
        "semantic": semantic,
        "method": "full" if semantic is not None else "vader_only",
    }

    surface = vader.get("overall_sentiment")
    depth = semantic.get("semantic_valence") if semantic else None
    if isinstance(surface, (int, float)) and isinstance(depth, (int, float)):
        gap = round(depth - surface, 4)
        result["interpretation_gap"] = {
            "vader_surface": surface,
            "semantic_depth": depth,
            "gap": gap,
            "description": (
                "darker than they sound"
                if gap < -0.2
                else "brighter than they sound"
                if gap > 0.2
                else "surface and depth align"
            ),
        }

    return cast("dict[str, object]", sanitize(result))
