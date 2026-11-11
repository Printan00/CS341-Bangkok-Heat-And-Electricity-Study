"""Read one Happy Home answer the same way in Validate and Transform.

`values` is one raw row ({column: value}); `c` is contracts/happy_home.json; `code` is a question
code from c["questions"] (e.g. "A7", "C2.5", "D1.1H"). Each reader returns (answer, state) with
state in blank / ok / invalid (A12 also: zero / unbanded).
"""
import math

from common.answers import band, canonical, flag, is_blank, key


def single(values, c, code):
    """Single-choice question -> (questionnaire spelling or None, state)."""
    q = c["questions"][code]
    v = values.get(q["column"])
    if is_blank(v):
        return None, "blank"
    a = canonical(v, q["allowed"])
    return (a, "ok") if a is not None else (None, "invalid")


def multi(values, c, code):
    """Multi-select question -> ({option label: 0/1/None or "bad"}, state)."""
    opts = c["questions"][code]["options"]
    flags = {lab: flag(values.get(o["column"])) for lab, o in opts.items()}
    if any(f == "bad" for f in flags.values()):
        return flags, "invalid"
    if all(f is None for f in flags.values()):
        return flags, "blank"
    return flags, "ok"


def a12(values, c):
    """A12 household size -> (band or None, state). A whole number >= 1 is 'unbanded' (V06/T03)."""
    v = values.get(c["questions"]["A12"]["column"])
    if is_blank(v):
        return None, "blank"
    b = canonical(v, c["household_size_bands"])
    if b is not None:
        return b, "ok"
    n = whole_number(v)
    if n == 0:
        return None, "zero"
    if n is not None and n >= 1:
        return None, "unbanded"
    return None, "invalid"


def state(values, c, code):
    if c["questions"][code]["kind"] == "multi":
        return multi(values, c, code)[1]
    if code == "A12":
        return a12(values, c)[1]
    return single(values, c, code)[1]


def whole_number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    k = key(v)
    return int(k) if k.isdigit() else None


def number(v):
    if isinstance(v, bool) or is_blank(v):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def size_band(n, bands):
    """T03: whole number of people -> its band ("2" -> "2–3", 7 -> "6+")."""
    for b in bands:
        k = key(b)
        if k.endswith("+") and n >= int(k[:-1]):
            return b
        lo, _, hi = k.partition("–")
        if int(lo) <= n <= int(hi or lo):
            return b
    return None


def bills(values, c):
    """(income, normal bill, summer bill) as band tuples (ordinal, min, max), or None when missing."""
    inc, _ = single(values, c, "A7")
    nb, _ = single(values, c, "E1.1")
    sb, _ = single(values, c, "E1.2")
    return (band(inc, c["income_bands"]) if inc else None,
            band(nb, c["bill_bands"]) if nb else None,
            band(sb, c["bill_bands"]) if sb else None)
