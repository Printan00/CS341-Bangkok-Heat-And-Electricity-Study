#!/usr/bin/env python3
"""Two-sided Fisher exact tests on the visible (n >= 5) cells of the Athena result CSVs, so the findings do not
over-read differences that small groups could produce by chance. Standard library only.

Usage: python analytics/significance.py [--results analytics/results] [--write]
Each row compares group A with group B on a yes/no outcome (x of n). p < 0.05 is only a rough guide with n = 88 and
many comparisons (no multiple-testing correction); the results are associations, not causes.
"""
import argparse
import csv
from math import comb
from pathlib import Path


def fisher(a, n1, b, n2):
    """two-sided Fisher exact p for [[a, n1-a], [b, n2-b]]"""
    k, n = a + b, n1 + n2

    def pr(x):
        return comb(n1, x) * comb(n2, k - x) / comb(n, k)
    lo, hi = max(0, k - n2), min(k, n1)
    obs = pr(a)
    return min(1.0, sum(pr(x) for x in range(lo, hi + 1) if pr(x) <= obs * (1 + 1e-9)))


def rows(results, name):
    return list(csv.DictReader(open(Path(results) / name, encoding="utf-8")))


def num(v):
    if v == "<5":
        raise ValueError("hidden cell used in a test")
    return int(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", default=Path(__file__).parent / "results", type=Path)
    ap.add_argument("--write", action="store_true", help="also write analytics/results/significance.csv")
    args = ap.parse_args()
    R = args.results
    q11 = {(r["feature"], r["level"]): r for r in rows(R, "q1_Q1_1.csv")}
    out = []

    def add(q, label, outcome, ga, gb):
        (a, n1), (b, n2) = ga, gb
        out.append({"q": q, "comparison": label, "outcome": outcome, "x_A": a, "n_A": n1, "pct_A": round(100 * a / n1, 1),
                    "x_B": b, "n_B": n2, "pct_B": round(100 * b / n2, 1), "fisher_p": round(fisher(a, n1, b, n2), 3)})

    def hv(feature, level):
        r = q11[(feature, level)]
        return num(r["n_high"]), num(r["n"])

    def pool(*parts):
        return sum(p[0] for p in parts), sum(p[1] for p in parts)

    add("Q1", "ระบายอากาศ ไม่ดี vs ดี", "ผลกระทบความร้อนสูง", hv("B8 ระบายอากาศ", "ไม่ดี"), hv("B8 ระบายอากาศ", "ดี"))
    add("Q1", "ผนังไม้ vs ผนังอื่น (คอนกรีต + ผสม/อื่น ๆ)", "ผลกระทบความร้อนสูง", hv("B3 วัสดุผนัง", "ไม้"),
        pool(hv("B3 วัสดุผนัง", "คอนกรีต"), hv("B3 วัสดุผนัง", "ผสม/สังกะสี/อื่น ๆ/ไม่ระบุ (รวม)")))
    add("Q1", "หลังคาสังกะสี/เมทัลชีท vs อื่น ๆ", "ผลกระทบความร้อนสูง", hv("B4 หลังคา", "สังกะสี/เมทัลชีท"),
        hv("B4 หลังคา", "กระเบื้อง/คอนกรีต/อื่น ๆ/ไม่ระบุ (รวม)"))
    add("Q1", "ไม่มีฝ้า vs มีฝ้า/ไม่แน่ใจ", "ผลกระทบความร้อนสูง", hv("B6 ฝ้าเพดาน", "ไม่มีฝ้า"), hv("B6 ฝ้าเพดาน", "มีฝ้า/ไม่แน่ใจ (รวม)"))
    q13 = {r["community_key"]: r for r in rows(R, "q1_Q1_3.csv")}
    add("Q1", "ชุมชนหลังแฟลต vs คนรักถิ่น", "ผลกระทบความร้อนสูง",
        (num(q13["หลังแฟลต"]["n_high"]), num(q13["หลังแฟลต"]["n"])), (num(q13["คนรักถิ่น"]["n_high"]), num(q13["คนรักถิ่น"]["n"])))
    q14 = {r["coping_limited"]: r for r in rows(R, "q1_Q1_4.csv")}
    add("Q1", "รับมือได้จำกัด (coping_limited) vs ไม่จำกัด", "ผลกระทบความร้อนสูง",
        (num(q14["true"]["n_high"]), num(q14["true"]["n"])), (num(q14["false"]["n_high"]), num(q14["false"]["n"])))
    q23 = {r["has_aircon"]: r for r in rows(R, "q2_Q2_3.csv")}
    add("Q2", "ไม่มีแอร์ vs มีแอร์", "ภาระค่าไฟสูง (>=10%)", (num(q23["false"]["n_high"]), num(q23["false"]["n"])),
        (num(q23["true"]["n_high"]), num(q23["true"]["n"])))
    q29 = {r["income_group"]: r for r in rows(R, "q2_Q2_9.csv")}
    g = list(q29.values())
    add("Q2", "รายได้ไม่เกิน 10,000 vs มากกว่า 10,000", "ภาระค่าไฟสูง (>=10%)", (num(g[0]["n_high"]), num(g[0]["n"])),
        (num(g[1]["n_high"]) + num(g[2]["n_high"]), num(g[1]["n"]) + num(g[2]["n"])))
    add("Q2", "รายได้ไม่เกิน 10,000 vs 10,001-20,000", "ภาระค่าไฟสูง (>=10%)", (num(g[0]["n_high"]), num(g[0]["n"])),
        (num(g[1]["n_high"]), num(g[1]["n"])))

    for r in out:
        print("%s | %s | %s: %d/%d (%.1f%%) vs %d/%d (%.1f%%) | Fisher p = %.3f" % (
            r["q"], r["comparison"], r["outcome"], r["x_A"], r["n_A"], r["pct_A"], r["x_B"], r["n_B"], r["pct_B"], r["fisher_p"]))
    if args.write:
        with open(R / "significance.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0]))
            w.writeheader()
            w.writerows(out)


if __name__ == "__main__":
    main()
