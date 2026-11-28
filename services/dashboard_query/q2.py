"""Public aggregate Q2 response. Athena applies disclosure rules before returning counts."""
from pathlib import Path

SQL = Path(__file__).with_name("q2.sql").read_text(encoding="utf-8")
COUNTS = ("high", "possibly_high", "low", "missing")
COLUMNS = ("breakdown", "income", "cooling", "households", *COUNTS)
INCOMES = {"lower", "middle", "upper", "unknown"}
COOLING = {"no", "yes", "unknown"}
DIMENSIONS = {
    "income": (INCOMES, {"all"}),
    "cooling": ({"all"}, COOLING),
    "combined": (INCOMES, COOLING),
}


def payload(rows):
    result, seen = [], set()
    for values in rows:
        breakdown, income, cooling = (values[key] for key in COLUMNS[:3])
        dimensions = DIMENSIONS.get(breakdown)
        identifiers = breakdown, income, cooling
        if dimensions is None or income not in dimensions[0] or cooling not in dimensions[1] or identifiers in seen:
            raise ValueError("Unexpected Q2 group")
        seen.add(identifiers)
        counts = {key: int(values[key]) if values[key] is not None else None for key in COLUMNS[3:]}
        households = counts["households"]
        burden = [counts[key] for key in COUNTS]
        if households is not None and households < 5:
            raise ValueError("Unexpected Q2 group size")
        if any(value is not None for value in burden) and (
            households is None or any(value is None or 0 < value < 5 or value < 0 for value in burden)
            or sum(burden) != households
        ):
            raise ValueError("Unexpected Q2 disclosure state")
        result.append({"breakdown": breakdown, "income": income, "cooling": cooling, **counts})
    return {"rows": result}
