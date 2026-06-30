"""semantic_lyrics.analyze: lyric acquisition, degrade paths, and ISSUE-009 URL encoding."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING

import httpx

from claudes_ears.analysis import semantic_lyrics

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_LLM_JSON = {
    "themes": ["loss"],
    "imagery": ["rain"],
    "semantic_valence": -0.5,
    "key_lines": [{"line": "I love you", "significance": "ironic"}],
}


class _Resp:
    """Minimal stand-in for httpx.Response — only status_code and json() are read."""

    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


def _lyrics_ok(*_a: object, **_k: object) -> _Resp:
    return _Resp(200, {"lyrics": "I love you so much\neverything is wonderful\nstay with me"})


def _llm_ok(*_a: object, **_k: object) -> _Resp:
    return _Resp(200, {"content": [{"type": "text", "text": json.dumps(_LLM_JSON)}]})


def test_happy_path_web_lyrics_and_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(semantic_lyrics.httpx, "get", _lyrics_ok)
    monkeypatch.setattr(semantic_lyrics.httpx, "post", _llm_ok)

    result = semantic_lyrics.analyze({"stem_dir": "/stems/Artist - Title"})

    assert isinstance(result, dict)
    assert result["available"] is True
    assert result["source"] == "lyrics.ovh"
    assert result["method"] == "full"
    semantic = result["semantic"]
    assert isinstance(semantic, dict)
    assert semantic["method"] == "claude_api"
    gap = result["interpretation_gap"]
    assert isinstance(gap, dict)
    assert gap["semantic_depth"] == -0.5
    assert gap["description"] == "darker than they sound"


def test_transcription_fallback_uses_faster_whisper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "Artist - Title").mkdir()
    stem_dir = tmp_path / "Artist - Title"
    (stem_dir / "vocals.wav").write_bytes(b"RIFF")

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(semantic_lyrics.httpx, "get", lambda *a, **k: _Resp(404, {}))
    fake_model = SimpleNamespace(
        transcribe=lambda *a, **k: (
            iter([SimpleNamespace(text=" first line "), SimpleNamespace(text="second")]),
            object(),
        )
    )
    monkeypatch.setattr(semantic_lyrics, "_load_whisper_model", lambda: fake_model)

    result = semantic_lyrics.analyze({"stem_dir": str(stem_dir)})

    assert result["available"] is True
    assert result["source"] == "whisper"
    assert result["line_count"] == 2
    assert result["method"] == "vader_only"


def test_missing_api_key_degrades_to_vader_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(semantic_lyrics.httpx, "get", _lyrics_ok)

    def _no_post(*_a: object, **_k: object) -> _Resp:
        raise AssertionError("LLM must not be called without an API key")

    monkeypatch.setattr(semantic_lyrics.httpx, "post", _no_post)

    result = semantic_lyrics.analyze({"stem_dir": "/stems/Artist - Title"})

    assert result["available"] is True
    assert result["semantic"] is None
    assert result["method"] == "vader_only"


def test_llm_network_failure_degrades_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(semantic_lyrics.httpx, "get", _lyrics_ok)

    def _boom(*_a: object, **_k: object) -> _Resp:
        raise httpx.ConnectError("network down")

    monkeypatch.setattr(semantic_lyrics.httpx, "post", _boom)

    result = semantic_lyrics.analyze({"stem_dir": "/stems/Artist - Title"})

    assert result["available"] is True
    assert result["semantic"] is None
    assert result["method"] == "vader_only"


def test_fetch_lyrics_url_encodes_reserved_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def _capture(url: str, **_k: object) -> _Resp:
        captured["url"] = url
        return _Resp(404, {})

    monkeypatch.setattr(semantic_lyrics.httpx, "get", _capture)

    semantic_lyrics._fetch_lyrics_web("AC/DC", "Hello?")

    assert "AC%2FDC" in captured["url"]
    assert "Hello%3F" in captured["url"]
    assert "/v1/AC/DC/" not in captured["url"]


def test_no_lyrics_source_returns_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(semantic_lyrics.httpx, "get", lambda *a, **k: _Resp(404, {}))
    result = semantic_lyrics.analyze({"stem_dir": str(tmp_path / "untitled")})
    assert result["available"] is False
    assert result["method"] == "unavailable"
