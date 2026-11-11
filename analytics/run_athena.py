#!/usr/bin/env python3
"""Run the analytics/*.sql statements on Athena (workgroup bhes-wg, database bhes) and save one CSV per statement:
analytics/results/<q1|q2|q3|data_quality>/<Qx_y>.csv  (the statement id comes from its '-- Qx.y' comment).

Usage (AWS CLI credentials with Athena + the results bucket access, region ap-southeast-1):
    python analytics/run_athena.py                 # every .sql file in analytics/
    python analytics/run_athena.py analytics/q2_burden_by_income_cooling.sql
Every statement already hides cells with 1-4 households ('<5'); the script saves exactly what Athena returns.
Needs: aws CLI (v2). No other packages.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent


def aws(*args):
    r = subprocess.run(["aws", *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout


def statements(path):
    text = Path(path).read_text(encoding="utf-8")
    return [s.strip() for s in re.split(r";\s*\n", text) if "SELECT" in s]


def run(stmt, workgroup):
    qid = aws("athena", "start-query-execution", "--work-group", workgroup,
              "--query-execution-context", "Database=bhes", "--query-string", stmt,
              "--query", "QueryExecutionId", "--output", "text").strip()
    while True:
        q = json.loads(aws("athena", "get-query-execution", "--query-execution-id", qid))["QueryExecution"]
        if q["Status"]["State"] not in ("QUEUED", "RUNNING"):
            return qid, q
        time.sleep(1.5)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--results", default=HERE / "results", type=Path)
    ap.add_argument("--workgroup", default="bhes-wg")
    ap.add_argument("--region", default="ap-southeast-1")
    args = ap.parse_args()
    os.environ.setdefault("AWS_DEFAULT_REGION", args.region)
    files = args.files or sorted(HERE.glob("*.sql"))
    failed = []
    for f in files:
        for stmt in statements(f):
            m = re.search(r"^-- (Q\d+\.\d+)", stmt, re.M)
            name = m.group(1).replace(".", "_") if m else Path(f).stem
            folder = name.split("_")[0].lower() if m else "data_quality"
            qid, q = run(stmt, args.workgroup)
            state = q["Status"]["State"]
            if state != "SUCCEEDED":
                print(name, state, q["Status"].get("StateChangeReason", "")[:200])
                failed.append(name)
                continue
            dest = args.results / folder / (name + ".csv")
            dest.parent.mkdir(parents=True, exist_ok=True)
            aws("s3", "cp", q["ResultConfiguration"]["OutputLocation"], str(dest))
            print("%-14s ok  scanned %s bytes -> %s" % (name, q.get("Statistics", {}).get("DataScannedInBytes"), dest))
    if failed:
        sys.exit("failed: %s" % failed)


if __name__ == "__main__":
    main()
