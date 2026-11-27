"""The community LST CSV written by scripts/gee_lst.py: parsing shared by Validate, Transform and Verify.

One row per community: community, n_households, lst_mean_c, n_scenes, period (start..end), buffer_m, source.
No coordinates: the script reads household points locally and writes only the community summary.
"""
import csv
import io
import re

PERIOD = re.compile(r"^(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})$")


def read_csv(data):
    """bytes -> (header, [(source_row, row dict)]). The header is row 1, so data starts at row 2.

    Raises UnicodeDecodeError or csv.Error for a file that is not a UTF-8 CSV.
    """
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
    rows = list(enumerate(reader, start=2))
    return [h.strip() for h in (reader.fieldnames or [])], [(i, {k.strip(): v for k, v in r.items() if k})
                                                             for i, r in rows]


def period(text):
    """'2026-03-01..2026-05-31' -> ('2026-03-01', '2026-05-31'), None when malformed or start >= end."""
    m = PERIOD.match((text or "").strip())
    if not m or m.group(1) >= m.group(2):
        return None
    return m.group(1), m.group(2)


def number(text):
    """CSV text -> float, None when blank or not a finite number."""
    try:
        v = float((text or "").strip())
    except ValueError:
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def integer(text):
    v = number(text)
    return int(v) if v is not None and v == int(v) else None


# The two Earth Engine sources: same CSV shape and rules, different key (one row per community / household).
SOURCES = {
    "gee_lst": {"key": "community", "out_key": "community_key", "rules": "gee_lst",
                "trusted": "trusted_gee_lst", "curated": "curated_community_dim", "table": "community_dim",
                "risk_columns": ("lst_mean_c", "lst_score", "lst_batch_id")},
    "gee_lst_household": {"key": "household_code", "out_key": "household_code", "rules": "gee_lst_household",
                          "trusted": "trusted_gee_lst_household", "curated": "curated_household_lst",
                          "table": "household_lst", "risk_columns": ("lst_hh_c", "lst_hh_score", "lst_hh_batch_id")},
}
