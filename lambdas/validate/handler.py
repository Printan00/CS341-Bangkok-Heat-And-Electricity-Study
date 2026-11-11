"""Validate step (#19): check each raw survey file of a batch, write quarantine/, tell Step Functions if valid.

Input event:  {"batch_id": "..."}  (+ optional "fail_at": "validate" to force a failure, as in the other stubs)
Reads:        raw/<source>/<batch_id>/<file>.xlsx   as written by scripts/ingest.py (batch_id = <source>-<sha12>,
              so a batch normally holds one source); every source folder with that batch_id is checked
Writes:       quarantine/<source>/<batch_id>/
                dq_report.json   counts only (per-rule counts below 5 shown as "<5")
                violations.csv   one line per broken rule
                rows.jsonl       quarantined raw rows with their rule_ids (empty when the batch stops)
                manifest.json    status + ids that passed (+ dq_flags, community_key) and ids quarantined
              All four are written on every run, so a rerun never leaves files from an earlier run.
Returns:      the event plus "valid" (False stops the pipeline at ValidationFailed) and a per-file summary.
Rules: reports/validation_rules.md. Standard library + boto3 only (both available in the Lambda runtime).
"""
import csv
import io
import json
import os

import happy_home
import sovi
from core import load_contract

VALIDATORS = {"happy_home": happy_home.validate, "sovi": sovi.validate}
ID_COLUMN = {"happy_home": "household_code", "sovi": "respondent_id"}


def handler(event, context):
    if event.get("fail_at") == "validate":
        raise RuntimeError("forced failure for testing")
    import boto3

    return run(event, s3=boto3.client("s3"), bucket=os.environ["LAKE_BUCKET"])


def run(event, s3, bucket, contracts=None):
    batch_id = event["batch_id"]
    found = _raw_files(s3, bucket, batch_id, contracts)
    if not found:
        raise FileNotFoundError("no raw .xlsx for batch_id=%s under raw/<source>/%s/" % (batch_id, batch_id))
    summaries = []
    for source, key in found:
        data = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        contract = (contracts or {}).get(source) or load_contract(source)
        result = VALIDATORS[source](data, contract, batch_id=batch_id)
        summaries.append(_write_outputs(s3, bucket, source, key, result, contract))
    return {**event, "valid": all(s["status"] == "passed" for s in summaries), "validation": summaries}


def _raw_files(s3, bucket, batch_id, contracts):
    sources = list(contracts) if contracts else list(VALIDATORS)
    found = []
    for source in sources:
        prefix = "raw/%s/%s/" % (source, batch_id)
        keys = [o["Key"] for o in s3.list_objects_v2(Bucket=bucket, Prefix=prefix).get("Contents", [])
                if o["Key"].lower().endswith(".xlsx")]
        if len(keys) > 1:
            raise ValueError("expected one .xlsx under %s, found %d" % (prefix, len(keys)))
        found += [(source, k) for k in keys]
    return found


def _put(s3, bucket, key, text, content_type):
    s3.put_object(Bucket=bucket, Key=key, Body=text.encode("utf-8"), ContentType=content_type)


def _write_outputs(s3, bucket, source, raw_key, result, contract):
    prefix = "quarantine/%s/%s/" % (source, result.batch_id)
    report = {**result.report(), "raw_key": raw_key}
    _put(s3, bucket, prefix + "dq_report.json", json.dumps(report, ensure_ascii=False, indent=1), "application/json")
    summary = {k: report[k] for k in ("source", "status", "rows_in", "rows_passed", "rows_quarantined")}
    summary.update(raw_key=raw_key, report_key=prefix + "dq_report.json", manifest_key=prefix + "manifest.json")

    buf = io.StringIO()
    buf.write("﻿")  # BOM so Excel shows Thai correctly
    w = csv.DictWriter(buf, fieldnames=["rule_id", "severity", "record_id", "source_row", "column", "message"])
    w.writeheader()
    for v in result.batch_violations + result.row_violations:
        w.writerow({k: v.to_dict()[k] for k in w.fieldnames})
    _put(s3, bucket, prefix + "violations.csv", buf.getvalue(), "text/csv")

    # Stopped at batch level (e.g. privacy gate): keep no row data, and say so in the manifest
    passed, quarantine = result.passed or [], result.quarantine or []
    rows = "\n".join(json.dumps(r, ensure_ascii=False, default=str) for r in quarantine)
    _put(s3, bucket, prefix + "rows.jsonl", rows, "application/x-ndjson")

    id_col = contract.get("id_column", ID_COLUMN[source])
    keep = [k for k in ("community_key", "community_code") if passed and k in passed[0]]
    manifest = {
        "source": source, "batch_id": result.batch_id, "status": result.status, "raw_key": raw_key,
        "source_sha256": result.sha256,
        "passed": [{"id": r[id_col], "dq_flags": r["dq_flags"], **{k: r[k] for k in keep}} for r in passed],
        "quarantined": [{"id": r[id_col], "rule_ids": r["rule_ids"]} for r in quarantine],
    }
    _put(s3, bucket, prefix + "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1), "application/json")
    return summary
