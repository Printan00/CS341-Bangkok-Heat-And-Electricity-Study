"""Validate step (#19): check one raw batch and write the results to quarantine/<source>/<batch_id>/.

Input: {"batch_id": "<source>-<sha12>"}. Output adds "valid" (Step Functions stops when false).
Files written every run (a rerun overwrites them, so nothing stale is left):
  dq_report.json   counts per rule and usable_q1..q3 (counts 1-4 shown as "<5")
  violations.csv   one line per row x rule
  rows.jsonl       the quarantined rows as they came in (has coordinates: keep quarantine/ restricted)
  manifest.json    status passed/failed + every passed row's dq_flags, usable flags and community
Rules: reports/validation_rules.md (rules live in validate/rules.py and common/contracts/happy_home.json)
"""
import csv
import hashlib
import io
import json
from datetime import datetime, timezone

from common import lake
from common.xlsx import read_workbook
from validate.rules import FAIL, QUESTIONS, validate

RULE_SOURCES = {"happy_home": "happy_home"}  # source -> contract name


def masked(n):
    return "<5" if 0 < n < 5 else n


def report(batch_id, source, raw_key, sha, errors, rows):
    passed = [r for r in rows if not r.failed]
    per_rule = {}
    for r in rows:
        for rule, level in {(rule, level) for rule, level, _ in r.violations}:
            per_rule.setdefault(rule, {"FAIL": 0, "WARN": 0})[level] += 1
    return {
        "batch_id": batch_id,
        "source": source,
        "raw_key": raw_key,
        "source_file_sha256": sha,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "valid": not errors and bool(passed),
        "batch_errors": errors,
        "rows_total": len(rows),
        "rows_passed": len(passed),
        "rows_quarantined": len(rows) - len(passed),
        "rules": {rule: {lv: masked(n) for lv, n in v.items() if n} for rule, v in sorted(per_rule.items())},
        "usable_in_passed_rows": {q: masked(sum(r.usable[q] for r in passed)) for q in QUESTIONS},
        "note": "counts 1-4 are shown as <5",
    }


def violations_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["source_row", "household_code", "rule", "level", "message"])
    for r in rows:
        for rule, level, msg in r.violations:
            w.writerow([r.source_row, r.household_code or "", rule, level, msg])
    return buf.getvalue().encode("utf-8-sig")  # BOM so Excel shows Thai correctly


def quarantined_jsonl(rows):
    lines = [json.dumps({"source_row": r.source_row,
                         "rules": sorted({rule for rule, lv, _ in r.violations if lv == FAIL}),
                         "values": r.values}, ensure_ascii=False, default=str)
             for r in rows if r.failed]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def manifest(batch_id, source, raw_key, sha, rep, rows):
    return {
        "batch_id": batch_id,
        "source": source,
        "raw_key": raw_key,
        "source_file_sha256": sha,
        "status": "passed" if rep["valid"] else "failed",
        "rows_total": len(rows),
        "passed": [{
            "household_code": r.household_code,
            "source_row": r.source_row,
            "dq_flags": r.dq_flags,
            "usable_q1": r.usable["q1"], "usable_q2": r.usable["q2"], "usable_q3": r.usable["q3"],
            "community_key": r.community_key,
            "community_source": r.community_source,
            "community_suggested": r.community_suggested,
            "a12_unbanded": r.a12_unbanded,
        } for r in rows if not r.failed],
        "quarantined": [{"household_code": r.household_code, "source_row": r.source_row,
                         "rules": sorted({rule for rule, lv, _ in r.violations if lv == FAIL})}
                        for r in rows if r.failed],
    }


def run(batch_id):
    source = lake.source_of(batch_id)
    raw_key = lake.raw_file(batch_id)
    data = lake.get_bytes(raw_key)
    sha = hashlib.sha256(data).hexdigest()

    if source not in RULE_SOURCES:
        errors, rows = ["ยังไม่มีกฎตรวจของ %s (สเปกตอนนี้ครอบคลุมเฉพาะ Happy Home) จึงไม่ส่งต่อ" % source], []
    else:
        try:
            sheets = read_workbook(data)
        except Exception as e:  # a broken file is a finding to report, not a crash
            errors, rows = ["เปิดไฟล์ .xlsx ไม่ได้ (%s)" % type(e).__name__], []
        else:
            errors, rows = validate(sheets, lake.contract(RULE_SOURCES[source]))

    rep = report(batch_id, source, raw_key, sha, errors, rows)
    q = lake.quarantine_prefix(batch_id)
    lake.put_json(q + "dq_report.json", rep)
    lake.put_bytes(q + "violations.csv", violations_csv(rows), "text/csv; charset=utf-8")
    lake.put_bytes(q + "rows.jsonl", quarantined_jsonl(rows), "application/x-ndjson")
    lake.put_json(q + "manifest.json", manifest(batch_id, source, raw_key, sha, rep, rows))
    return rep


def handler(event, context):
    lake.force_fail(event, "validate")
    rep = run(event["batch_id"])
    return {**event, "source": rep["source"], "valid": rep["valid"],
            "rows_passed": rep["rows_passed"], "rows_quarantined": rep["rows_quarantined"]}
