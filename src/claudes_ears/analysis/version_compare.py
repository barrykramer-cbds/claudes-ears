"""Version comparison (producer fingerprint, pair) — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from claudes_ears.models.perception import PerceptionDocument


def analyze(doc_a: PerceptionDocument, doc_b: PerceptionDocument) -> dict[str, object]:
    """Delta two PerceptionDocuments into producer-fingerprint changes.

    Two consolidated PerceptionDocuments.
    """
    raise NotImplementedError
