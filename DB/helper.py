# helpers.py
from __future__ import annotations

from typing import Optional, Literal, Dict, Any, Iterable, Tuple
import re

Bounds = Literal["[]", "[)", "(]", "()"]


# ------------------------------------------------------------
# int4range helpers
# ------------------------------------------------------------
def make_year_range(
    start: Optional[int] = None,
    end: Optional[int] = None,
    bounds: Bounds = "[)",
) -> str:
    """
    Build a PostgreSQL int4range literal for academic years.

    Examples
    --------
    make_year_range(None, None)        -> "[,]"
    make_year_range(2024, None)        -> "[2024,)"
    make_year_range(None, 2024, "[)")  -> "[,2024)"
    make_year_range(2020, 2024, "[]")  -> "[2020,2024]"
    """
    _validate_bounds(bounds)
    _validate_year(start, "start")
    _validate_year(end, "end")
    if start is not None and end is not None and start > end:
        raise ValueError(f"start must be <= end (got start={start}, end={end})")

    left, right = bounds[0], bounds[1]
    a = "" if start is None else str(start)
    b = "" if end is None else str(end)
    return f"{left}{a},{b}{right}"


def parse_year_range(range_literal: str) -> Tuple[Optional[int], Optional[int], Bounds]:
    """
    Parse a PostgreSQL int4range literal into (start, end, bounds).

    Accepts:
      - "[,]" "[2024,)" "[,2024)" "[2020,2024]"
    """
    s = range_literal.strip()
    m = re.fullmatch(r"([\[\(])\s*([^,]*)\s*,\s*([^)\]]*)\s*([\)\]])", s)
    if not m:
        raise ValueError(f"Invalid int4range literal: {range_literal}")

    left, a, b, right = m.group(1), m.group(2), m.group(3), m.group(4)
    bounds: Bounds = (left + right)  # type: ignore

    start = int(a) if a != "" else None
    end = int(b) if b != "" else None
    _validate_bounds(bounds)
    _validate_year(start, "start")
    _validate_year(end, "end")
    if start is not None and end is not None and start > end:
        raise ValueError(f"start must be <= end (got start={start}, end={end})")

    return start, end, bounds


def year_in_range(year: int, range_literal: str) -> bool:
    """
    Pure-Python check: does `year` fall inside int4range literal?

    Notes:
      - Honors inclusive/exclusive bounds.
      - This matches PostgreSQL semantics for discrete ints.

    Examples:
      year_in_range(2024, "[2024,)") -> True
      year_in_range(2024, "(2024,)") -> False
    """
    _validate_year(year, "year")
    start, end, bounds = parse_year_range(range_literal)

    left_inclusive = bounds[0] == "["
    right_inclusive = bounds[1] == "]"

    if start is not None:
        if left_inclusive:
            if year < start:
                return False
        else:
            if year <= start:
                return False

    if end is not None:
        if right_inclusive:
            if year > end:
                return False
        else:
            if year >= end:
                return False

    return True


# ------------------------------------------------------------
# JSON helpers (rules.condition / rules.action)
# ------------------------------------------------------------
def json_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Shallow merge. patch overwrites base.
    Useful for composing condition/action fragments.
    """
    out = dict(base)
    out.update(patch)
    return out


def compact_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove keys whose values are None, empty list/dict/string.
    Useful when you want clean JSON for rules.
    """
    def keep(v: Any) -> bool:
        if v is None:
            return False
        if isinstance(v, (str, list, dict)) and len(v) == 0:
            return False
        return True

    return {k: v for k, v in d.items() if keep(v)}


# ------------------------------------------------------------
# Validations
# ------------------------------------------------------------
def _validate_bounds(bounds: str) -> None:
    if bounds not in ("[]", "[)", "(]", "()"):
        raise ValueError(f"bounds must be one of [] [) (] () (got {bounds})")


def _validate_year(y: Optional[int], name: str) -> None:
    if y is None:
        return
    if not isinstance(y, int):
        raise TypeError(f"{name} must be int or None (got {type(y)})")
    # academic year sanity window (tweak freely)
    if y < 1900 or y > 2200:
        raise ValueError(f"{name} out of expected range (1900~2200): {y}")
