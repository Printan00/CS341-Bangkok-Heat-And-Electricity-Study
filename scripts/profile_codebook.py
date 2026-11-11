#!/usr/bin/env python3
"""Profile the two household surveys and write a variable dictionary.

Reads the anonymized Excel files from data/ (never committed) and writes ONLY
aggregates to reports/: variable names, question text, type, value sets,
missing %, and data-quality counts. No household rows, no coordinates, and any
count below K_MIN is shown as "<5".

Usage:
    python scripts/profile_codebook.py [--data-dir data] [--out reports]
Requires: openpyxl (see scripts/requirements.txt)
"""
import argparse
import collections
import csv
import json
import re
from pathlib import Path

import openpyxl

K_MIN = 5            # suppress counts below this
MAX_VALUESET = 12    # list value sets only for columns with <= this many distinct values

HH_FILE = "ThaiCI_Household_Questionaire/ThaiCI_Household_Questionaire_anonymized.xlsx"
SOVI_FILE = "SOVI_Survey_Questionaire/SOVI_Survey_Questionaire_anonymized.xlsx"

# Happy Home columns whose header is only a bare label ("น้ำท่วม", "ความร้อน.2",
# "ไฟฟ้า"...). They are the cells of grid questions (rows = hazard or option,
# columns = flood / heat). Mapped by position using the questionnaire (.docx)
# order; each range was checked against that order (see reports/data_dictionary.md).
HH_GRID_MAP = [
    (147, 148, "D1.1", "รายได้ได้รับผลกระทบ (grid: น้ำท่วม/ความร้อน)"),
    (149, 165, "D1.2", "สาเหตุที่กระทบรายได้ (grid: สาเหตุ x น้ำท่วม/ความร้อน)"),
    (166, 167, "D1.3", "มูลค่าค่าใช้จ่าย/รายได้ที่ลดลง (grid)"),
    (168, 169, "D2.1", "ปัญหาสุขภาพจากภัย (grid)"),
    (170, 186, "D2.1b", "อาการ/ปัญหาสุขภาพ (grid: อาการ x น้ำท่วม/ความร้อน)"),
    (187, 188, "D2.2", "ความเครียด/กังวล (grid)"),
    (189, 190, "D2.3", "ความตึงเครียดในครอบครัว (grid)"),
    (191, 222, "D3.1", "บริการที่หยุดชะงัก (grid: บริการ x น้ำท่วม/ความร้อน)"),
    (223, 224, "D3.2", "เข้าไม่ถึงความช่วยเหลือ (grid)"),
    (289, 290, "G1", "ใครรับภาระดูแลเมื่อเกิดภัย (grid)"),
    (291, 292, "G2", "ใครเสียรายได้มากที่สุด (grid)"),
    (293, 294, "G3", "ใครอยู่บ้านมากที่สุด (grid)"),
    (297, 298, "G6", "กลุ่มที่เดินทาง/ใช้พื้นที่ลำบาก (grid)"),
]

# Question-id -> research question tags (Q1 housing & heat, Q2 energy burden,
# Q3 prioritisation / capacity).
def hh_tags(qid, header):
    tags = set()
    if re.match(r"^(B[3-9]|B10|B11|C2\.|D1\.|D2\.|D3\.)", qid):
        tags.add("Q1")
    if qid in ("A7", "A8", "A12") or qid.startswith("E1") or qid.startswith("E2"):
        tags.add("Q2")
    if qid in ("A7", "A8", "A10", "A11", "A13", "A6", "B12", "D3.2", "E3.1", "E3.2", "E3.3", "C2.8") \
            or qid.startswith(("F", "G", "H", "I")):
        tags.add("Q3")
    return ",".join(sorted(tags))


def hazard_of(header, qid):
    if "ความร้อน" in header or "ร้อน" in header:
        return "heat"
    if "น้ำท่วม" in header or "น้ำขัง" in header:
        return "flood"
    if qid.startswith("C2") or qid in ("B11",):
        return "heat" if qid.startswith("C2") else "mixed"
    if qid.startswith("C1"):
        return "flood"
    return ""


def read_sheet(wb, name):
    ws = wb[name]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def is_na(v):
    return v is None or (isinstance(v, str) and v.strip() in ("", "None"))


def supp(n):
    return "<%d" % K_MIN if 0 < n < K_MIN else str(n)


HAZARD_TEXT = {"น้ำท่วม", "ความร้อน", "น้ำท่วม ความร้อน"}


def distinct_vals(vals):
    return {str(v) for v in vals if not is_na(v)}


def infer_kind(header, values, headers_seen):
    nn = [v for v in values if not is_na(v)]
    distinct = {str(v) for v in nn}
    if not nn:
        return "empty"
    if distinct <= {"0", "1"} and all(isinstance(v, (int, float)) for v in nn):
        return "multi_child_flag"
    if all(isinstance(v, (int, float)) for v in nn):
        return "numeric_or_score"
    if len(distinct) <= MAX_VALUESET:
        return "single_choice"
    if "ตอบได้มากกว่า 1 ข้อ" in header:
        return "multi_parent_text"
    return "free_text_or_id"


def parse_hh(path, out_rows, summary):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    data = read_sheet(wb, "Data")
    H, R = data[0], data[1:]
    summary["happy_home"] = {"rows": len(R), "columns": len(H)}
    grid = {}
    for lo, hi, qid, desc in HH_GRID_MAP:
        for i in range(lo, hi + 1):
            grid[i] = (qid, desc)
    parents = {}
    for i, h in enumerate(H):
        h = "" if h is None else str(h)
        vals = [r[i] if i < len(r) else None for r in R]
        if i in grid:
            qid, desc = grid[i]
            question = desc
            section = qid[0]
        else:
            m = re.match(r"^([A-I]\d+(?:\.\d+)?)[. ]", h)
            qid = m.group(1) if m else ""
            section = qid[0] if qid else ""
            question = h
        child_of = ""
        if "/" in h:
            prefix = h.rsplit("/", 1)[0]
            if prefix in parents:
                child_of = parents[prefix]
        if h and h not in parents:
            parents[h] = i
        lat_lon = "พิกัด" in h or "latitude" in h or "longitude" in h
        kind = "coordinate_EXCLUDED" if lat_lon else infer_kind(h, vals, None)
        if child_of != "" and kind == "multi_child_flag":
            kind = "multi_child_flag"
        if i in grid and kind == "single_choice" and distinct_vals(vals) <= HAZARD_TEXT:
            kind = "grid_hazard_text"   # cell holds which hazard(s) the option applies to
        if i in (0, 5) or h in ("household_code", "interviewer_code"):
            kind = "pseudonymous_id"
        if h == "ชื่อชุมชน":
            kind = "community_label(dirty)"
        if h == "วันที่สัมภาษณ์":
            kind = "month_only"
        n = len(vals)
        miss = sum(1 for v in vals if is_na(v))
        distinct = {str(v) for v in vals if not is_na(v)}
        valueset = ""
        if kind in ("single_choice", "grid_hazard_text", "multi_child_flag", "month_only", "numeric_or_score") \
                and len(distinct) <= MAX_VALUESET:
            c = collections.Counter(str(v) for v in vals if not is_na(v))
            valueset = "; ".join("%s=%s" % (k, supp(v)) for k, v in sorted(c.items()))
        out_rows.append({
            "dataset": "happy_home", "col_index": i, "question_id": qid, "section": section,
            "header": h.replace("\n", " "), "kind": kind,
            "hazard": hazard_of(h, qid), "n_distinct": len(distinct),
            "missing_pct": round(100.0 * miss / n, 1) if n else 0,
            "value_set_counts": valueset,
            "question_tags": hh_tags(qid, h), "parent_col": child_of,
        })
    return H, R


def parse_sovi(path, out_rows, summary):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    data = read_sheet(wb, "ใส่ค่าคะแนน")
    key = read_sheet(wb, "ค่าคะแนน")
    H, R = data[0], data[1:]
    summary["sovi"] = {"rows": len(R), "columns": len(H), "score_key_rows": len(key) - 1}
    # item number -> factor group from the scoring key sheet
    group = {}
    for r in key[1:]:
        if r[0] not in (None, "None") and str(r[0]).isdigit():
            group[int(r[0])] = (r[1], r[2])
    for i, h in enumerate(H):
        h = "" if h is None else str(h)
        vals = [r[i] if i < len(r) else None for r in R]
        m = re.match(r"^\s*[vV]\s*_?(\d+)", h)
        is_score = bool(m) and not re.match(r"^\d", h)
        m2 = m or re.match(r"^\s*(\d+)", h)
        item = int(m2.group(1)) if m2 else None
        topic, grp = group.get(item, ("", ""))
        kind = "score_column" if is_score else infer_kind(h, vals, None)
        if h == "respondent_id":
            kind = "pseudonymous_id"
        if h == "หมายเลขพื้นที่":
            kind = "community_label"
        n = len(vals)
        miss = sum(1 for v in vals if is_na(v))
        distinct = {str(v) for v in vals if not is_na(v)}
        valueset = ""
        if kind in ("single_choice", "score_column", "numeric_or_score") and len(distinct) <= MAX_VALUESET:
            c = collections.Counter(str(v) for v in vals if not is_na(v))
            valueset = "; ".join("%s=%s" % (k, supp(v)) for k, v in sorted(c.items()))
        out_rows.append({
            "dataset": "sovi", "col_index": i, "question_id": item if item is not None else "",
            "section": grp, "header": h.replace("\n", " ")[:160], "kind": kind,
            "hazard": "flood/water" if re.search("น้ำท่วม|อุทกภัย|แล้ง|ขาดแคลนน้ำ", h) else "",
            "n_distinct": len(distinct),
            "missing_pct": round(100.0 * miss / n, 1) if n else 0,
            "value_set_counts": valueset, "question_tags": "", "parent_col": "",
        })
    return H, R


def hh_checks(H, R, summary):
    idx = {h: i for i, h in enumerate(H)}
    def c(name):
        return [r[idx[name]] for r in R]
    chk = {}
    ids = c("household_code")
    chk["duplicate_household_codes"] = len(ids) - len(set(ids))
    # community normalisation
    cm = collections.Counter()
    for v in c("ชื่อชุมชน"):
        s = str(v)
        if "คนรักถิ่น" in s or "ชุมนคนรักถิ่น" in s:
            cm["คนรักถิ่น"] += 1
        elif "แฟลต" in s:
            cm["หลังแฟลต"] += 1
        else:
            cm["unclassifiable"] += 1
    chk["community_raw_distinct_labels"] = len(set(map(str, c("ชื่อชุมชน"))))
    chk["community_normalised_counts"] = {k: supp(v) if k == "unclassifiable" else str(v) for k, v in cm.items()}
    bands = ["ต่ำกว่า 500 บาท", "500–1,000 บาท", "1,001–2,000 บาท", "2,001–3,000 บาท", "มากกว่า 3,000 บาท"]
    e1 = [r[idx[next(h for h in H if str(h).startswith("E1.1"))]] for r in R]
    e2 = [r[idx[next(h for h in H if str(h).startswith("E1.2"))]] for r in R]
    chk["summer_bill_band_below_normal"] = supp(sum(1 for a, b in zip(e1, e2)
                                                   if a in bands and b in bands and bands.index(b) < bands.index(a)))
    inc = [r[idx[next(h for h in H if str(h).startswith("A7."))]] for r in R]
    exp = [r[idx[next(h for h in H if str(h).startswith("A8."))]] for r in R]
    ib = ["ต่ำกว่า 5,000 บาท", "5,001–10,000 บาท", "10,001–20,000 บาท", "20,001–50,000 บาท", "มากกว่า 50,000 บาท"]
    chk["income_band_below_expense_band"] = supp(sum(1 for a, b in zip(inc, exp)
                                                    if a in ib and b in ib and ib.index(a) < ib.index(b)))
    chk["lowest_income_band_and_summer_bill_over_3000"] = supp(
        sum(1 for a, b in zip(inc, e2) if a == ib[0] and b == bands[-1]))
    la, lo = idx["_พิกัดครัวเรือน (ปักหมุด)_latitude"], idx["_พิกัดครัวเรือน (ปักหมุด)_longitude"]
    chk["rows_missing_coordinates"] = supp(sum(1 for r in R if is_na(r[la]) or is_na(r[lo])))
    def _f(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None
    pts = [(_f(r[la]), _f(r[lo])) for r in R]
    inside = [p for p in pts if p[0] and p[1] and 13.5 <= p[0] <= 14.1 and 100.3 <= p[1] <= 100.9]
    present = [p for p in pts if p[0] is not None and p[1] is not None]
    chk["coordinates_inside_bangkok_bbox"] = len(inside)
    chk["coordinates_present_but_outside_bbox"] = supp(len(present) - len(inside))
    chk["distinct_rounded_coordinate_pairs_inside"] = len(set(inside))
    chk["interview_month_values"] = sorted({str(v) for v in c("วันที่สัมภาษณ์")})
    # Settings sheet (anonymisation parameters)
    summary["happy_home_checks"] = chk


def sovi_checks(H, R, summary):
    idx = {h: i for i, h in enumerate(H)}
    chk = {}
    ids = [r[0] for r in R]
    chk["duplicate_respondent_ids"] = len(ids) - len(set(ids))
    chk["distinct_community_labels"] = len({r[1] for r in R})
    chk["community_labels_with_numeric_code_prefix"] = sum(
        1 for r in R if re.match(r"^\(\d+\)", str(r[1])))
    kw = re.compile("ไฟฟ้า|ไฟ(?!ส่อง)|พลังงาน|แอร์|พัดลม|เครื่องปรับ|อุณหภูมิ|ความร้อน|ร้อน")
    chk["headers_mentioning_heat_or_energy_use"] = [
        str(h).replace("\n", " ")[:90] for h in H if h and kw.search(str(h))]
    chk["columns_over_50pct_missing"] = sum(
        1 for i in range(len(H)) if sum(1 for r in R if is_na(r[i])) > len(R) / 2)
    chk["columns_over_90pct_missing"] = sum(
        1 for i in range(len(H)) if sum(1 for r in R if is_na(r[i])) > 0.9 * len(R))
    summary["sovi_checks"] = chk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default="reports")
    a = ap.parse_args()
    data_dir, out = Path(a.data_dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    summary, rows = {}, []
    hh_H, hh_R = parse_hh(data_dir / HH_FILE, rows, summary)
    hh_checks(hh_H, hh_R, summary)
    sv_H, sv_R = parse_sovi(data_dir / SOVI_FILE, rows, summary)
    sovi_checks(sv_H, sv_R, summary)
    fields = ["dataset", "col_index", "question_id", "section", "header", "kind", "hazard",
              "n_distinct", "missing_pct", "value_set_counts", "question_tags", "parent_col"]
    for ds in ("happy_home", "sovi"):
        with open(out / ("%s_variables.csv" % ds), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(r for r in rows if r["dataset"] == ds)
    with open(out / "profile_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
