#!/usr/bin/env python3
"""Build the self-contained dashboard (one HTML file) from the Athena result CSVs.

Every number on the page is read from analytics/results/**.csv (nothing is typed by hand); the SQL text shown next to
each chart is read from analytics/*.sql. The build refuses to run if a count of 1-4 households appears in a count column
(the privacy rule: cells under 5 must already be hidden as "<5"), or if the last verification had mismatches.

Usage:
    python dashboard/build.py                      # writes dashboard/index.html (standalone page)
    python dashboard/build.py --format artifact --out /tmp/page.html   # fragment for an embedded viewer (no <html>/<head>)
Standard library only.
"""
import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "analytics" / "results"
COUNT_COLS = re.compile(r"^(n|n_.*|c_.*|x_A|n_A|x_B|n_B)$")


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def statements(sql_path):
    """-> {id: (title, sql)} using the '-- Qx.y title' comment that starts each statement"""
    out = {}
    text = sql_path.read_text(encoding="utf-8")
    for part in re.split(r";\s*\n", text):
        lines = part.strip().splitlines()
        for i, line in enumerate(lines):
            m = re.match(r"^-- (Q\d+\.\d+)\s*(.*)$", line)
            if m:
                out[m.group(1)] = (m.group(2).strip(), "\n".join(lines[i:]).strip() + ";")
                break
    return out


def leak_check(qid, rows):
    for r in rows:
        for k, v in r.items():
            if COUNT_COLS.match(k) and v in ("1", "2", "3", "4"):
                sys.exit("PRIVACY: %s column %s holds a count of %s (must be hidden as <5)" % (qid, k, v))
            if re.search(r"household|latitude|longitude", k, re.I):
                sys.exit("PRIVACY: %s has a column named %s" % (qid, k))


def collect():
    sql = {}
    for p in sorted((ROOT / "analytics").glob("*.sql")):
        sql.update(statements(p))
    data = {}
    newest = 0.0
    for p in sorted(RESULTS.glob("q*/*.csv")):
        qid = p.stem.replace("_", ".")
        rows = read_csv(p)
        leak_check(qid, rows)
        title, text = sql.get(qid, ("", ""))
        if not text:
            sys.exit("no SQL statement found for %s" % qid)
        data[qid] = {"title": title, "file": str(p.relative_to(ROOT / "analytics" / "results")), "sql": text, "rows": rows}
        newest = max(newest, p.stat().st_mtime)
    dq = RESULTS / "data_quality" / "data_quality.csv"
    rows = read_csv(dq)
    leak_check("DQ", [{k: v for k, v in r.items() if k != "item"} for r in rows])
    data["DQ"] = {"title": "data quality", "file": "data_quality/data_quality.csv", "sql": "", "rows": rows}
    sig = read_csv(RESULTS / "significance.csv")
    leak_check("significance", sig)
    meta = {"runDate": dt.datetime.fromtimestamp(newest, dt.timezone(dt.timedelta(hours=7))).strftime("%Y-%m-%d"), "compared": "?"}
    ver = RESULTS / "verification.json"
    if ver.exists():
        v = json.loads(ver.read_text(encoding="utf-8"))
        if v.get("mismatches"):
            sys.exit("verification reports %s mismatches; fix before building" % v["mismatches"])
        meta["compared"] = v["compared"]
    else:
        print("note: analytics/results/verification.json missing; run analytics/compare_athena_local.py --write", file=sys.stderr)
    return {"meta": meta, "q": data, "sig": sig}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--format", choices=["page", "artifact"], default="page")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    out = args.out or ROOT / "dashboard" / "index.html"
    tpl = (ROOT / "dashboard" / "template.html").read_text(encoding="utf-8")
    head, body = tpl.split("<!--BODY-->")
    payload = json.dumps(collect(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    body = body.replace("/*DATA*/", payload)
    if args.format == "page":
        html = ('<!doctype html>\n<html lang="th">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + head.strip() + "\n</head>\n<body>\n" + body.strip() + "\n</body>\n</html>\n")
        # standalone page has no host padding: add a small reset the embedded viewer provides itself
        html = html.replace("</style>", "html{color-scheme:light dark}body{margin:0}</style>", 1)
    else:
        html = head.strip() + "\n" + body.strip() + "\n"
    out.write_text(html, encoding="utf-8")
    print("wrote %s (%d KB)" % (out, len(html) // 1024))


if __name__ == "__main__":
    main()
