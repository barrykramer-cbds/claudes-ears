"""Boundary sanitizer: non-finite floats null out, structure is preserved."""

import math

from claudes_ears._sanitize import sanitize


def test_nan_and_inf_become_none() -> None:
    out = sanitize({"a": math.nan, "b": math.inf, "c": -math.inf, "d": 1.5})
    assert out == {"a": None, "b": None, "c": None, "d": 1.5}


def test_nested_structures_recurse() -> None:
    out = sanitize({"xs": [1, math.nan, {"y": math.inf}], "ok": "text"})
    assert out == {"xs": [1, None, {"y": None}], "ok": "text"}


def test_finite_values_and_types_pass_through() -> None:
    payload = {"i": 0, "f": 0.0, "s": "x", "b": True, "n": None}
    assert sanitize(payload) == payload


def test_tuples_become_lists() -> None:
    assert sanitize((1, 2.0, math.nan)) == [1, 2.0, None]
