#!/usr/bin/env python3
"""Compare every visible cell of selected Athena result CSVs with recheck_local.py (an independent recomputation
from the raw file). Cells hidden as '<5' are skipped. Exit code 1 if any visible cell differs.

Usage: python analytics/compare_athena_local.py [--data-dir data] [--results analytics/results]
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import recheck_local as L  # noqa: E402

HEAT = ["low", "medium", "high", "missing"]
BUR = ["high", "possibly_high", "low", "burden_missing"]
checked = bad = skipped = 0


def cmp(label, athena, local):
    global checked, bad, skipped
    if athena == "<5":
        skipped += 1
        return
    checked += 1
    if str(athena) != str(local):
        bad += 1
        print("MISMATCH", label, "athena=%s local=%s" % (athena, local))


def table(results, name):
    return list(csv.DictReader(open(results / name, encoding="utf-8")))


def heat_counts(rows):
    c = Counter(d["heat_level"] or "missing" for d in rows)
    return {"low": c["low"], "medium": c["medium"], "high": c["high"], "heat_missing": c["missing"]}


def heat2_counts(rows):
    c = Counter(d["heat_level"] or "missing" for d in rows)
    return {"high": c["high"], "not_high": c["low"] + c["medium"], "heat_missing": c["missing"]}


def check_heat2(label, a, rows):
    cmp(label + " n", a["n"], len(rows))
    for k, v in heat2_counts(rows).items():
        cmp(label + " n_" + k, a["n_" + k], v)
    if rows and any(d["heat_score"] is not None for d in rows):
        sc = [d["heat_score"] for d in rows if d["heat_score"] is not None]
        cmp(label + " avg score", a["avg_heat_score"], "%.2f" % (sum(sc) / len(sc)) if False else str(round(sum(sc) / len(sc), 2)))


def bur_counts(rows, key="burden_class_10"):
    c = Counter(d[key] or "burden_missing" for d in rows)
    return {"high": c["high"], "possibly_high": c["possibly_high"], "low": c["low"], "burden_missing": c["burden_missing"]}


def check_heat(label, a, rows):
    cmp(label + " n", a["n"], len(rows))
    for k, v in heat_counts(rows).items():
        cmp(label + " n_" + k, a["n_" + k], v)


def check_bur(label, a, rows, key="burden_class_10", ranges=False):
    cmp(label + " n", a["n"], len(rows))
    for k, v in bur_counts(rows, key).items():
        cmp(label + " n_" + k, a["n_" + k], v)
    if ranges:
        mins = [d["burden_min"] for d in rows if "burden_min" in d]
        maxs = [d["burden_max"] for d in rows if "burden_max" in d]
        if mins:
            cmp(label + " lowest burden_min", a["burden_min_lowest_pct"], round(100 * min(mins), 1))
            cmp(label + " highest burden_max", a["burden_max_highest_pct"], round(100 * max(maxs), 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", default="data", type=Path)
    ap.add_argument("--results", default=Path(__file__).parent / "results", type=Path)
    args = ap.parse_args()
    rows = L.compute(L.Sheet(args.data_dir / L.FILE))
    R = args.results
    # Q1.1: merged categories, same recoding as analytics/q1_heat_by_housing.sql (written out here independently)
    recode = {
        "B4 หลังคา": ("roof", lambda v: "สังกะสี/เมทัลชีท" if v == "สังกะสี/เมทัลชีท" else "กระเบื้อง/คอนกรีต/อื่น ๆ/ไม่ระบุ (รวม)"),
        "B3 วัสดุผนัง": ("wall", lambda v: v if v in ("ไม้", "คอนกรีต") else "ผสม/สังกะสี/อื่น ๆ/ไม่ระบุ (รวม)"),
        "B6 ฝ้าเพดาน": ("ceiling", lambda v: "ไม่มีฝ้า" if v == "ไม่มี" else "มีฝ้า/ไม่แน่ใจ (รวม)"),
        "B7 ฉนวน": ("insulation", lambda v: "ไม่มีฉนวน" if v == "ไม่มี" else "มีฉนวน/ไม่แน่ใจ (รวม)"),
        "B8 ระบายอากาศ": ("ventilation", lambda v: v if v is not None else "(ไม่ระบุ/ไม่แน่ใจ)"),
        "B9 ร่มเงา": ("shade", lambda v: v if v is not None else "(ไม่ระบุ/ไม่แน่ใจ)"),
    }
    for a in table(R, "q1_Q1_1.csv"):
        if a["feature"] in recode:
            key, f = recode[a["feature"]]
            sub = [d for d in rows if f(d[key]) == a["level"]]
            check_heat2("Q1.1 %s=%s" % (a["feature"], a["level"]), a, sub)
    def band(v):
        return "(null)" if v is None else ("0-1" if v <= 1 else ("2" if v == 2 else ("3" if v == 3 else "4-5")))
    for a in table(R, "q1_Q1_2.csv"):
        sub = [d for d in rows if band(d["housing_heat_score"]) == a["housing_heat_score_band"]]
        check_heat2("Q1.2 band=%s" % a["housing_heat_score_band"], a, sub)
    for a in table(R, "q1_Q1_4.csv"):
        sub = [d for d in rows if str(d["coping_limited"] if d["coping_limited"] is not None else "(null)").lower() == a["coping_limited"]]
        check_heat("Q1.4 coping=%s" % a["coping_limited"], a, sub)
    for a in table(R, "q2_Q2_1.csv"):
        sub = [d for d in rows if (d["income_ord"] or 0) == int(a["income_ord"])]
        check_bur("Q2.1 income=%s" % a["income_ord"], a, sub, ranges=True)
    for a in table(R, "q2_Q2_2.csv"):
        sub = [d for d in rows if (d["income_ord"] or 0) == int(a["income_ord"])]
        check_bur("Q2.2 income=%s (6%%)" % a["income_ord"], a, sub, key="burden_class_6")
    for a in table(R, "q2_Q2_3.csv"):
        sub = [d for d in rows if str(d["has_aircon"] == 1).lower() == a["has_aircon"]]
        check_bur("Q2.3 aircon=%s" % a["has_aircon"], a, sub, ranges=True)
    for a in table(R, "q2_Q2_4.csv"):
        sub = [d for d in rows if (d["income_ord"] or 0) == int(a["income_ord"]) and str(d["has_aircon"] == 1).lower() == a["has_aircon"]]
        check_bur("Q2.4 income=%s aircon=%s" % (a["income_ord"], a["has_aircon"]), a, sub)
    for a in table(R, "q2_Q2_7.csv"):
        sub = [d for d in rows if str(d["has_fan"]) == a["has_fan"]]
        check_bur("Q2.7 fan=%s" % a["has_fan"], a, sub)
    print("compared %d visible cells, %d hidden (<5) skipped, %d mismatches" % (checked, skipped, bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
