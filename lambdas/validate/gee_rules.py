"""Validate rules G01-G10 for the Earth Engine LST CSVs (reports/gee_lst_pipeline.md).

Two sources share the rules; only the key differs (common/gee.py SOURCES):
  gee_lst            one row per community, key column `community`
  gee_lst_household  one row per household, key column `household_code`

Batch rules (FAIL stops the whole batch, nothing goes on):
  G01 the file is a UTF-8 CSV
  G02 every required column is there
  G03 no coordinate columns (and no community name in the household file): summaries only
  G09 every passed row has the same period, buffer_m and source (else the values are not comparable)
  G10 WARN (community only): a Happy Home community has no row (its households will get no LST)
Row rules (FAIL quarantines the row):
  G04 the key is valid: a community key of happy_home.json community_map / a non-blank household_code
  G05 the key appears once
  G06 lst_mean_c is a number inside the plausible range (gee_lst.json lst_plausible_c)
  G07 n_scenes is a whole number >= 1
  G08 period is YYYY-MM-DD..YYYY-MM-DD with start < end, buffer_m > 0 and source is not blank
"""
import csv
from collections import Counter
from dataclasses import dataclass, field

from common.gee import integer, number, period, read_csv

FAIL, WARN = "FAIL", "WARN"


@dataclass
class GeeRow:
    source_row: int
    key: str
    values: dict
    violations: list = field(default_factory=list)

    @property
    def failed(self):
        return any(level == FAIL for _, level, _ in self.violations)


def validate(data, contract, plausible, key_column, allowed=None):
    """-> (batch errors, batch warnings, rows).

    plausible: (low, high) deg C. allowed: the valid keys (communities), or None = any non-blank key.
    """
    try:
        header, raw = read_csv(data)
    except (UnicodeDecodeError, csv.Error) as e:
        return ["G01 อ่านไฟล์เป็น CSV (UTF-8) ไม่ได้ (%s)" % type(e).__name__], [], []
    missing = [c for c in contract["required_columns"] if c not in header]
    if missing:
        return ["G02 ไม่มีคอลัมน์ที่ต้องมี: %s" % ", ".join(missing)], [], []
    private = [c for c in header if c in contract["forbidden_columns"]]
    if private:  # do not keep the rows: they would carry the coordinates into quarantine/
        return ["G03 มีคอลัมน์ต้องห้าม %s ไฟล์ต้องเป็นค่าสรุปที่ไม่มีพิกัดเท่านั้น" % ", ".join(private)], [], []

    lo, hi = plausible
    counts = Counter((r.get(key_column) or "").strip() for _, r in raw)
    rows = []
    for source_row, r in raw:
        key = (r.get(key_column) or "").strip()
        row = GeeRow(source_row, key, r)
        if not key or (allowed is not None and key not in allowed):
            row.violations.append(("G04", FAIL, "%s %r ว่างหรือไม่อยู่ในค่าที่รู้จัก" % (key_column, key)))
        if key and counts[key] > 1:
            row.violations.append(("G05", FAIL, "%s %r มี %d แถว" % (key_column, key, counts[key])))
        lst = number(r.get("lst_mean_c"))
        if lst is None or not lo <= lst <= hi:
            row.violations.append(("G06", FAIL, "lst_mean_c %r ไม่ใช่ตัวเลขในช่วง %g–%g °C (ว่าง = ไม่มีพิกเซลไร้เมฆ)"
                                   % (r.get("lst_mean_c"), lo, hi)))
        scenes = integer(r.get("n_scenes"))
        if scenes is None or scenes < 1:
            row.violations.append(("G07", FAIL, "n_scenes %r ต้องเป็นจำนวนเต็ม ≥ 1" % r.get("n_scenes")))
        buffer_m = number(r.get("buffer_m"))
        if period(r.get("period")) is None or buffer_m is None or buffer_m <= 0 or not (r.get("source") or "").strip():
            row.violations.append(("G08", FAIL, "period/buffer_m/source ไม่ถูกรูปแบบ (%r, %r, %r)"
                                   % (r.get("period"), r.get("buffer_m"), r.get("source"))))
        rows.append(row)

    errors, warnings = [], []
    passed = [r for r in rows if not r.failed]
    settings = {(period(r.values["period"]), number(r.values["buffer_m"]), r.values["source"].strip()) for r in passed}
    if len(settings) > 1:
        errors.append("G09 แถวที่ผ่านใช้ช่วงภาพ/รัศมี/แหล่งภาพต่างกัน %d แบบ เทียบกันไม่ได้" % len(settings))
    if allowed is not None:
        absent = sorted(set(allowed) - {r.key for r in passed})
        if absent:
            warnings.append("G10 ไม่มีค่า LST ของ %s บ้านในชุมชนนั้นจะได้ LST เป็น null" % ", ".join(absent))
    return errors, warnings, rows
