"""Boundary sanitizer (schema §5): non-finite floats -> None, numpy -> native
Python. Per-field int/float coercion is the models' job, not this helper's.
"""

from __future__ import annotations

from collections.abc import Mapping
import math


def sanitize(value: object) -> object:
    """Recursively null non-finite floats and coerce numpy values to native Python.

    str/bytes/None/bool pass through; exotic leaves (set, Decimal) are left as-is.
    """
    if isinstance(value, Mapping):
        return {str(key): sanitize(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]

    # bool is an int subclass — preserve it before the numeric branches.
    if isinstance(value, bool):
        return value

    # numpy scalars and ndarrays both expose tolist(); str/bytes/list do not
    # reach here, so this only catches numpy-like objects.
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return sanitize(tolist())

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    return value
