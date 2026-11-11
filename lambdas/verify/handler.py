"""Verify step (#22): a finished run is not proof the data is right, so check before publishing.

Checks the staged curated table against trusted/, Validate's manifest and the raw file:
  1. row counts: raw = passed + quarantined; manifest passed = trusted = curated
  2. the same household ids, each once, in manifest, trusted and curated
  3. schema: column names and types exactly as in the schema contracts (nothing extra, e.g. coordinates)
  4. required fields (nullable=false in the contract) have no nulls
  5. totals: usable_q1..q3, has_aircon and burden_class counts agree between trusted and curated
When everything passes: publish staging -> curated/<table>/part-0.parquet, then write
curated/_pipeline/success/<batch_id>/_SUCCESS.json (for CheckBatch). Otherwise raise VerifyFailed,
which fails the Step Functions execution with the reasons, and nothing is published.
"""
from collections import Counter
from datetime import datetime, timezone

from common import lake, parquet
from common.xlsx import read_workbook

TABLE = "happy_home_household"
TOTALS = ["usable_q1", "usable_q2", "usable_q3", "has_aircon", "burden_class"]


class VerifyFailed(Exception):
    pass


def schema_problems(table, contract, label):
    expected = parquet.schema(contract)
    got = table.schema
    problems = []
    if got.names != expected.names:
        extra = sorted(set(got.names) - set(expected.names))
        missing = sorted(set(expected.names) - set(got.names))
        problems.append("%s columns differ from the contract (extra %s, missing %s)" % (label, extra, missing))
    else:
        for f in expected:
            if not got.field(f.name).type.equals(f.type):
                problems.append("%s.%s is %s, contract says %s" % (label, f.name, got.field(f.name).type, f.type))
    bad = [n for n in got.names if n in contract["forbidden_columns"]]
    if bad:
        problems.append("%s has forbidden columns %s" % (label, bad))
    return problems


def null_problems(rows, contract, label):
    required = [c["name"] for c in contract["columns"] if not c["nullable"]]
    problems = []
    for name in required:
        n = sum(1 for r in rows if r.get(name) is None)
        if n:
            problems.append("%s.%s has %d null values" % (label, name, n))
    return problems


def id_problems(ids, label):
    dup = [k for k, n in Counter(ids).items() if n > 1]
    return ["%s has %d repeated household ids" % (label, len(dup))] if dup else []


def checks(raw_rows, manifest, trusted_tbl, curated_tbl, trusted_contract, curated_contract):
    """-> (problems, summary). Pure function so tests can call it without S3."""
    trusted, curated = trusted_tbl.to_pylist(), curated_tbl.to_pylist()
    passed = manifest["passed"]
    p = []
    if manifest.get("status") != "passed":
        p.append("manifest status is %r" % manifest.get("status"))
    if raw_rows != manifest["rows_total"]:
        p.append("raw has %d rows, Validate counted %d" % (raw_rows, manifest["rows_total"]))
    if raw_rows != len(passed) + len(manifest["quarantined"]):
        p.append("raw %d != passed %d + quarantined %d" % (raw_rows, len(passed), len(manifest["quarantined"])))
    if not (len(passed) == len(trusted) == len(curated)):
        p.append("row counts differ: passed %d, trusted %d, curated %d" % (len(passed), len(trusted), len(curated)))
    if not trusted:
        p.append("no rows to publish")
    ids = {"manifest": [r["household_code"] for r in passed],
           "trusted": [r.get("household_code") for r in trusted],
           "curated": [r.get("household_code") for r in curated]}
    for label, v in ids.items():
        p += id_problems(v, label)
    if not (set(ids["manifest"]) == set(ids["trusted"]) == set(ids["curated"])):
        p.append("household ids differ between manifest, trusted and curated")
    p += schema_problems(trusted_tbl, trusted_contract, "trusted")
    p += schema_problems(curated_tbl, curated_contract, "curated")
    p += null_problems(trusted, trusted_contract, "trusted")
    p += null_problems(curated, curated_contract, "curated")
    totals = {}
    for col in TOTALS:
        t = Counter(r.get(col) for r in trusted)
        c = Counter(r.get(col) for r in curated)
        if t != c:
            p.append("totals of %s differ between trusted and curated" % col)
        totals[col] = {str(k): v for k, v in sorted(t.items(), key=lambda kv: str(kv[0]))}
    summary = {"raw_rows": raw_rows, "passed": len(passed), "quarantined": len(manifest["quarantined"]),
               "trusted_rows": len(trusted), "curated_rows": len(curated), "totals": totals}
    return p, summary


def run(batch_id):
    if lake.source_of(batch_id) != "happy_home":
        raise ValueError("no verify step for source %r" % lake.source_of(batch_id))
    manifest = lake.get_json(lake.quarantine_prefix(batch_id) + "manifest.json")
    rules = lake.contract("happy_home")
    raw_rows = len(read_workbook(lake.get_bytes(manifest["raw_key"]))[rules["data_sheet"]].rows)
    staging = lake.staging_key(batch_id, TABLE)
    curated_bytes = lake.get_bytes(staging)
    problems, summary = checks(
        raw_rows, manifest,
        parquet.read(lake.get_bytes(lake.trusted_key(batch_id))), parquet.read(curated_bytes),
        lake.contract("trusted_happy_home"), lake.contract("curated_happy_home_household"))
    if problems:
        raise VerifyFailed("; ".join(problems))
    published = lake.curated_key(TABLE)
    lake.put_bytes(published, curated_bytes)
    marker = {"batch_id": batch_id, "status": "SUCCEEDED", "table": TABLE, "curated_key": published,
              "source_file_sha256": manifest["source_file_sha256"],
              "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **summary}
    lake.put_json(lake.success_key(batch_id), marker)
    return marker


def handler(event, context):
    lake.force_fail(event, "verify")
    marker = run(event["batch_id"])
    return {**event, "verified": True, "success_key": lake.success_key(event["batch_id"]),
            "curated_key": marker["curated_key"]}
