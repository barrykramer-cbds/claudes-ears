"""Semantic lyric reading (VADER + grounded LLM) — stub."""

from __future__ import annotations


def analyze(context: dict[str, object]) -> dict[str, object]:
    """Fetch lyrics and produce VADER + grounded-LLM semantic analysis (owns the Claude call).

    ``context`` carries track meta / transcript.
    """
    raise NotImplementedError
