"""Serialize Athena's disclosure-safe Q1 results and compare the binary cohorts."""

from collections import defaultdict
from math import comb
from pathlib import Path

SQL = Path(__file__).with_name("q1.sql").read_text(encoding="utf-8")
COLUMNS = ("kind", "dimension", "label", "households", "high", "value", "suppressed", "low", "medium")


def fisher_exact(first, second):
    """Two-sided Fisher exact test on the two groups' high-impact counts."""
    size = first["households"] + second["households"]
    row = first["households"]
    total_high = first["high"] + second["high"]
    fixed_score = comb(total_high, first["high"]) * comb(size - total_high, row - first["high"])
    lo, hi = max(0, row + total_high - size), min(row, total_high)
    likelihoods = (comb(total_high, high) * comb(size - total_high, row - high) for high in range(lo, hi + 1))
    return sum(score for score in likelihoods if score <= fixed_score) / comb(size, row)


def payload(raw_rows):
    rows = []
    comparisons = defaultdict(list)
    for raw in raw_rows:
        visibility = raw["suppressed"]
        if visibility not in {"true", "false"}:
            raise ValueError("Invalid Q1 disclosure result")
        suppressed = visibility == "true"
        row = {
            "kind": raw["kind"], "dimension": raw["dimension"], "label": raw["label"],
            "households": None if suppressed or raw["households"] is None else int(raw["households"]),
            "high": None if suppressed or raw["high"] is None else int(raw["high"]),
            "value": None if suppressed or raw["value"] is None else float(raw["value"]),
            "suppressed": suppressed,
            "low": None if suppressed or raw["low"] is None else int(raw["low"]),
            "medium": None if suppressed or raw["medium"] is None else int(raw["medium"]),
        }
        if not suppressed and (
            row["households"] is None or row["households"] < 5
            or any(row[key] is not None and 0 < row[key] < 5 for key in ("low", "medium", "high"))
            or (row["high"] is not None and 0 < row["households"] - row["high"] < 5)
        ):
            raise ValueError("Unsafe Q1 count")
        rows.append(row)
        if row["kind"] == "comparison":
            comparisons[row["dimension"]].append(row)

    return {
        "rows": rows,
        "pValues": {
            feature: fisher_exact(*cohorts)
            for feature, cohorts in comparisons.items()
            if len(cohorts) == 2 and all(row["high"] is not None for row in cohorts)
        },
    }
