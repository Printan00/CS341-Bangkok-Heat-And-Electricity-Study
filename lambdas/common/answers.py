"""Shared answer helpers for Validate (V03, V08-V10) and Transform (T01, T02, T06, T07).

Validate compares answers in this normalised form but never edits them; Transform writes the
canonical questionnaire spelling (T01). Rules: reports/validation_rules.md
"""
import re

_DASHES = re.compile(r"[-‐‑‒–—−]")
_SPACE = re.compile(r"\s+")


def is_blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


def key(v):
    """Comparison key: no spaces at all, every dash -> '–' ("ทุกคนพอๆกัน" == "ทุกคนพอ ๆ กัน")."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return _DASHES.sub("–", _SPACE.sub("", str(v)))


def canonical(v, allowed):
    """The questionnaire spelling of answer v, or None when v is blank or not an allowed answer."""
    if is_blank(v):
        return None
    k = key(v)
    for a in allowed:
        if key(a) == k:
            return a
    return None


def flag(v):
    """Multi-select 0/1 column -> 0, 1, None (blank) or "bad" (anything else)."""
    if is_blank(v):
        return None
    k = key(v)
    if k in ("0", "0.0", "False"):
        return 0
    if k in ("1", "1.0", "True"):
        return 1
    return "bad"


def band(label, table):
    """Canonical band label -> (ordinal 1..n, min, max) from a contract band table."""
    for i, (name, lo, hi) in enumerate(table, start=1):
        if name == label:
            return i, lo, hi
    return None


def burden(bill, income):
    """T07: bill and income are (ordinal, min, max). Returns (burden_min, burden_max)."""
    return bill[1] / income[2], bill[2] / income[1]


def burden_class(bmin, bmax, threshold):
    """high when even the lowest estimate reaches the threshold, possibly_high when only the highest does."""
    if bmin >= threshold:
        return "high"
    if bmax >= threshold:
        return "possibly_high"
    return "low"
