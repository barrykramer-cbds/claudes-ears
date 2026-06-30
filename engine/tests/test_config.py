"""Env-driven path config honors the env var and falls back to the default."""

from pathlib import Path

import pytest

from claudes_ears import config


def test_stems_dir_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.STEMS_ENV, raising=False)
    assert config.stems_dir() == config.DEFAULT_STEMS_DIR


def test_stems_dir_honors_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.STEMS_ENV, "/data/stems")
    assert config.stems_dir() == Path("/data/stems")


def test_music_dir_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.MUSIC_ENV, raising=False)
    assert config.music_dir() == config.DEFAULT_MUSIC_DIR


def test_music_dir_honors_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.MUSIC_ENV, "/library/music")
    assert config.music_dir() == Path("/library/music")
