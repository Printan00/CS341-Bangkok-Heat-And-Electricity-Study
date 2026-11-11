#!/usr/bin/env python3
"""Independent local recomputation of the Happy Home indicators, for spot-checking the Athena results (#24).

It reads the RAW survey xlsx and applies the rules of reports/validation_rules.md (T06 band bounds, T07 burden,
T09 housing score, T10 heat impact and coping limit) with its own code: it does NOT import lambdas/ or use any
pipeline output, so agreement with Athena means two separate implementations gave the same numbers.

Usage: python analytics/recheck_local.py [--data-dir data] [--json]
Prints aggregate counts only (no household ids, no coordinates). Needs openpyxl.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import openpyxl

FILE = "ThaiCI_Household_Questionaire/ThaiCI_Household_Questionaire_anonymized.xlsx"
DASHES = "-‐‑‒—−"
UNSURE = {"ไม่แน่ใจ", "ไม่ประสงค์จะระบุ"}

INCOME = {"ต่ำกว่า 5,000 บาท": (1, 2500, 5000), "5,001–10,000 บาท": (2, 5001, 10000),
          "10,001–20,000 บาท": (3, 10001, 20000), "20,001–50,000 บาท": (4, 20001, 50000),
          "มากกว่า 50,000 บาท": (5, 50001, 100000)}
BILL = {"ต่ำกว่า 500 บาท": (1, 0, 499), "500–1,000 บาท": (2, 500, 1000), "1,001–2,000 บาท": (3, 1001, 2000),
        "2,001–3,000 บาท": (4, 2001, 3000), "มากกว่า 3,000 บาท": (5, 3001, 6000)}
HEAT_LEVEL = {"ร้อนมากทุกวัน": 3, "ร้อนบ่อย": 2, "ร้อนบางวัน": 1, "ไม่ค่อยร้อน": 0}
EFFECTS = ["นอนไม่หลับ", "อยู่ในบ้านไม่สบาย", "ปวดหัว/อ่อนเพลีย", "ทำงานลำบาก", "เด็กเรียนหนังสือลำบาก"]
VULNERABLE = ["ผู้สูงอายุ", "ผู้พิการ", "ผู้ป่วยเรื้อรัง", "ผู้ป่วยติดเตียง"]


def norm(v):
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v).strip()
    if s in ("", "None"):
        return None
    return "".join("–" if ch in DASHES else ch for ch in s)


class Sheet:
    def __init__(self, path):
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        rows = [list(r) for r in wb["Data"].iter_rows(values_only=True)]
        self.header, self.rows = rows[0], rows[1:]
        self.index = {}
        for i, h in enumerate(self.header):
            self.index.setdefault(str(h).strip() if h is not None else "", i)

    def col(self, prefix):
        """first column whose header starts with prefix (single-answer question text)"""
        for h, i in self.index.items():
            if h.startswith(prefix):
                return i
        raise KeyError(prefix)

    def flag(self, parent_prefix, option):
        """multi-answer option column: '<question text>/<option>'"""
        for h, i in self.index.items():
            if h.startswith(parent_prefix) and h.endswith("/" + option):
                return i
        raise KeyError(parent_prefix + "/" + option)


def single(row, i):
    v = norm(row[i])
    return None if v is None or v in UNSURE else v


def flags(row, sheet, parent, options):
    out = {}
    for o in options:
        v = row[sheet.flag(parent, o)]
        out[o] = v if v in (0, 1) else None
    return out


def compute(sheet):
    c = {k: sheet.col(k) for k in ["A7.", "E1.1", "E1.2", "A14.", "A10.", "G8.", "C2.1", "C2.8", "B4.", "B6.", "B7.", "B8.", "B9."]}
    heat_cols = {"D1.1": sheet.index["ความร้อน"], "D2.1": sheet.index["ความร้อน.1"], "D2.2": sheet.index["ความร้อน.2"]}
    out = []
    for r in sheet.rows:
        a7, e12, e11 = single(r, c["A7."]), single(r, c["E1.2"]), single(r, c["E1.1"])
        inc, bil = INCOME.get(a7), BILL.get(e12)
        d = {"income_ord": inc[0] if inc else None, "bill_summer_ord": bil[0] if bil else None}
        if inc and bil:
            lo, hi = bil[1] / inc[2], bil[2] / inc[1]
            for tag, t in (("10", 0.10), ("6", 0.06)):
                d["burden_class_" + tag] = "high" if lo >= t else ("possibly_high" if hi >= t else "low")
            d["burden_min"], d["burden_max"] = lo, hi
        else:
            d["burden_class_10"] = d["burden_class_6"] = None
        ap = flags(r, sheet, "E2.1", ["เครื่องปรับอากาศ", "พัดลม"])
        d["has_aircon"], d["has_fan"] = ap["เครื่องปรับอากาศ"], ap["พัดลม"]
        # housing heat score: 1 point per risky answer, null when fewer than 4 answered clearly
        risky = {"B4.": {"สังกะสี/เมทัลชีท"}, "B6.": {"ไม่มี"}, "B7.": {"ไม่มี"}, "B8.": {"ไม่ดี"}, "B9.": {"น้อย", "ไม่มีเลย"}}
        ans = [(single(r, c[k]), v) for k, v in risky.items()]
        got = [(a, v) for a, v in ans if a is not None]
        d["housing_heat_score"] = sum(a in v for a, v in got) if len(got) >= 4 else None
        # heat impact 0-13
        lvl = single(r, c["C2.1"])
        eff = flags(r, sheet, "C2.5", EFFECTS)
        if lvl in HEAT_LEVEL and all(v is not None for v in eff.values()):
            s = HEAT_LEVEL[lvl] + sum(v == 1 for v in eff.values())
            s += {"มาก": 2, "บางส่วน": 1}.get(single(r, heat_cols["D1.1"]), 0)
            s += 1 if single(r, heat_cols["D2.1"]) == "เคย" else 0
            s += {"มาก": 2, "ปานกลาง": 1}.get(single(r, heat_cols["D2.2"]), 0)
            d["heat_score"] = s
            d["heat_level"] = "low" if s <= 4 else ("medium" if s <= 7 else "high")
        else:
            d["heat_score"], d["heat_level"] = None, None
        # coping limit 0-6
        tenure = single(r, c["A14."])
        cop = flags(r, sheet, "C2.7", ["ไม่มีวิธีรับมือ"])
        if tenure is not None and cop["ไม่มีวิธีรับมือ"] is not None:
            mem = flags(r, sheet, "A13", VULNERABLE)
            bar = flags(r, sheet, "B12", ["ไม่มีงบประมาณ"])
            k = sum([tenure != "เป็นเจ้าของเอง", single(r, c["A10."]) == "ไม่มี", bar["ไม่มีงบประมาณ"] == 1,
                     any(v == 1 for v in mem.values()), single(r, c["G8."]) == "ไม่มี", cop["ไม่มีวิธีรับมือ"] == 1])
            d["coping_limit"], d["coping_limited"] = k, k >= 3
        else:
            d["coping_limit"], d["coping_limited"] = None, None
        d["roof"] = single(r, c["B4."])
        for key, pre in (("wall", "B3."), ("ceiling", "B6."), ("insulation", "B7."), ("ventilation", "B8."), ("shade", "B9.")):
            d[key] = single(r, sheet.col(pre))
        d["retrofit"] = single(r, c["C2.8"])
        out.append(d)
    return out


def summary(rows):
    cnt = lambda key: dict(sorted(Counter(str(d[key]) for d in rows).items()))
    s = {"rows": len(rows)}
    for k in ["burden_class_10", "burden_class_6", "has_aircon", "has_fan", "heat_level", "coping_limited",
              "income_ord", "housing_heat_score", "retrofit"]:
        s[k] = cnt(k)
    # Q2.1-style: income_ord x burden_class (10%)
    s["income_x_burden10"] = {str(i): dict(sorted(Counter(str(d["burden_class_10"]) for d in rows if d["income_ord"] == i).items()))
                              for i in sorted({d["income_ord"] for d in rows if d["income_ord"]})}
    # Q2: median-free range check, lowest/highest burden per income band
    s["income_burden_range_pct"] = {str(i): [round(100 * min(d["burden_min"] for d in rows if d["income_ord"] == i and "burden_min" in d), 1),
                                              round(100 * max(d["burden_max"] for d in rows if d["income_ord"] == i and "burden_max" in d), 1)]
                                    for i in sorted({d["income_ord"] for d in rows if d["income_ord"]})
                                    if any("burden_min" in d for d in rows if d["income_ord"] == i)}
    # Q1.1-style: roof x heat level
    s["roof_x_heat"] = {str(r): dict(sorted(Counter(str(d["heat_level"]) for d in rows if d["roof"] == r).items()))
                        for r in sorted({d["roof"] for d in rows if d["roof"]})}
    s["avg_heat_score"] = round(sum(d["heat_score"] for d in rows if d["heat_score"] is not None) /
                                max(1, sum(d["heat_score"] is not None for d in rows)), 2)
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", default="data", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    s = summary(compute(Sheet(args.data_dir / FILE)))
    print(json.dumps(s, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
