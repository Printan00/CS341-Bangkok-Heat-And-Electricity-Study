"""Verify step (#22): a finished run is not proof the data is right, so check before publishing.

Checks the staged curated tables (happy_home_household and the five-group happy_home_risk) against
trusted/, Validate's manifest and the raw file:
  1. row counts: raw = passed + quarantined; manifest passed = trusted = curated = risk
  2. the same household ids, each once, in manifest, trusted, curated and risk
  3. schema: column names and types exactly as in the schema contracts (nothing extra, e.g. coordinates)
  4. required fields (nullable=false in the contract) have no nulls
  5. totals: usable_q1..q3, has_aircon and burden_class counts agree between trusted and curated
  6. risk table: every group score and both axes in 0-1, risk_score in 0-100 and equal to 100 x the mean
     of the five groups plus lst_hh_score when it is there (D27/D28; null exactly when a survey group is null)
  7. risk table LST (D21/D25): lst_mean_c / lst_score / lst_batch_id equal the published community_dim row of
     the household's community, lst_hh_c / lst_hh_score / lst_hh_batch_id equal the published household_lst
     row of the household (all null when there is none), and every score = the fixed 30-45 deg C scale
gee batches (community_dim / household_lst): raw rows = passed + quarantined; passed = trusted = table with the
same keys, each once; schema and nulls per contract; lst_mean_c plausible; lst_score recomputed.
When everything passes: publish both staging tables -> curated/<table>/part-0.parquet, then write
curated/_pipeline/success/<batch_id>/_SUCCESS.json (for CheckBatch). Otherwise raise VerifyFailed,
which fails the Step Functions execution with the reasons, and nothing is published.
"""
from collections import Counter
from datetime import datetime, timezone

from common import lake, parquet
from common.gee import SOURCES as GEE_SOURCES
from common.gee import read_csv
from common.xlsx import read_workbook

TABLE = "happy_home_household"
RISK_TABLE = "happy_home_risk"
GROUPS = ["heat_risk", "housing_risk", "finance_risk", "burden_risk", "coping_risk"]
UNIT_SCORES = GROUPS + ["exposure", "vulnerability"]  # kept apart from integrate/scoring.py on purpose
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


def risk_problems(rows):
    """The five-group table: scores inside their ranges and the total recomputed from the groups."""
    outside = sum(1 for r in rows for c in UNIT_SCORES if r.get(c) is not None and not 0 <= r[c] <= 1)
    outside += sum(1 for r in rows if r.get("risk_score") is not None and not 0 <= r["risk_score"] <= 100)
    wrong = 0
    for r in rows:
        groups = [r.get(g) for g in GROUPS]
        parts = groups + ([r["lst_hh_score"]] if r.get("lst_hh_score") is not None else [])
        expected = None if any(v is None for v in groups) else 100 * sum(parts) / len(parts)
        got = r.get("risk_score")
        if (expected is None) != (got is None) or (expected is not None and abs(expected - got) > 1e-4):
            wrong += 1
    p = []
    if outside:
        p.append("risk has %d scores outside 0-1 (risk_score outside 0-100)" % outside)
    if wrong:
        p.append("risk has %d rows where risk_score is not 100 x the mean of the five groups (+ LST)" % wrong)
    return p


def expected_lst_score(lst_c, score_range):
    """The fixed scale again, written apart from integrate/scoring.py on purpose."""
    lo, hi = score_range
    return min(1.0, max(0.0, (lst_c - lo) / (hi - lo)))


def lst_problems(trusted, risk, lst_rows, score_range, source="gee_lst"):
    """Every household carries the published LST of its community (gee_lst) or of itself (gee_lst_household),
    or nulls when there is none."""
    cfg = GEE_SOURCES[source]
    value_col, score_col, batch_col = cfg["risk_columns"]
    by_key = {d[cfg["out_key"]]: d for d in lst_rows}
    if source == "gee_lst":
        key_of = {t["household_code"]: t["community_key"] for t in trusted}
    else:
        key_of = {t["household_code"]: t["household_code"] for t in trusted}
    wrong = bad_score = 0
    for r in risk:
        d = by_key.get(key_of.get(r["household_code"]))
        want = (None, None, None) if d is None else (d["lst_mean_c"], d["lst_score"], d["batch_id"])
        if (r.get(value_col), r.get(score_col), r.get(batch_col)) != want:
            wrong += 1
        if r.get(value_col) is not None and (
                r.get(score_col) is None
                or abs(r[score_col] - expected_lst_score(r[value_col], score_range)) > 1e-6):
            bad_score += 1
    p = []
    if wrong:
        p.append("risk has %d rows whose %s is not the published %s value" % (wrong, value_col, cfg["table"]))
    if bad_score:
        p.append("risk has %d rows where %s is not the 30-45 deg C scale of %s" % (bad_score, score_col, value_col))
    return p


def checks(raw_rows, manifest, trusted_tbl, curated_tbl, risk_tbl, trusted_contract, curated_contract, risk_contract,
           dim_rows=(), score_range=(30.0, 45.0), hh_rows=()):
    """-> (problems, summary). Pure function so tests can call it without S3.

    dim_rows / hh_rows: the published community_dim / household_lst rows the risk table was joined with
    (empty before the first batch of that source).
    """
    trusted, curated, risk = trusted_tbl.to_pylist(), curated_tbl.to_pylist(), risk_tbl.to_pylist()
    passed = manifest["passed"]
    p = []
    if manifest.get("status") != "passed":
        p.append("manifest status is %r" % manifest.get("status"))
    if raw_rows != manifest["rows_total"]:
        p.append("raw has %d rows, Validate counted %d" % (raw_rows, manifest["rows_total"]))
    if raw_rows != len(passed) + len(manifest["quarantined"]):
        p.append("raw %d != passed %d + quarantined %d" % (raw_rows, len(passed), len(manifest["quarantined"])))
    if not (len(passed) == len(trusted) == len(curated) == len(risk)):
        p.append("row counts differ: passed %d, trusted %d, curated %d, risk %d"
                 % (len(passed), len(trusted), len(curated), len(risk)))
    if not trusted:
        p.append("no rows to publish")
    ids = {"manifest": [r["household_code"] for r in passed],
           "trusted": [r.get("household_code") for r in trusted],
           "curated": [r.get("household_code") for r in curated],
           "risk": [r.get("household_code") for r in risk]}
    for label, v in ids.items():
        p += id_problems(v, label)
    if not (set(ids["manifest"]) == set(ids["trusted"]) == set(ids["curated"]) == set(ids["risk"])):
        p.append("household ids differ between manifest, trusted, curated and risk")
    p += schema_problems(trusted_tbl, trusted_contract, "trusted")
    p += schema_problems(curated_tbl, curated_contract, "curated")
    p += schema_problems(risk_tbl, risk_contract, "risk")
    p += null_problems(trusted, trusted_contract, "trusted")
    p += null_problems(curated, curated_contract, "curated")
    p += null_problems(risk, risk_contract, "risk")
    p += risk_problems(risk)
    p += lst_problems(trusted, risk, dim_rows, score_range, "gee_lst")
    p += lst_problems(trusted, risk, hh_rows, score_range, "gee_lst_household")
    totals = {}
    for col in TOTALS:
        t = Counter(r.get(col) for r in trusted)
        c = Counter(r.get(col) for r in curated)
        if t != c:
            p.append("totals of %s differ between trusted and curated" % col)
        totals[col] = {str(k): v for k, v in sorted(t.items(), key=lambda kv: str(kv[0]))}
    summary = {"raw_rows": raw_rows, "passed": len(passed), "quarantined": len(manifest["quarantined"]),
               "trusted_rows": len(trusted), "curated_rows": len(curated), "risk_rows": len(risk), "totals": totals}
    return p, summary


def gee_checks(raw_rows, manifest, trusted_tbl, dim_tbl, trusted_contract, dim_contract, gee_contract,
               source="gee_lst"):
    """gee batch -> (problems, summary). Pure function so tests can call it without S3."""
    key, label = GEE_SOURCES[source]["out_key"], GEE_SOURCES[source]["table"]
    trusted, dim = trusted_tbl.to_pylist(), dim_tbl.to_pylist()
    passed = manifest["passed"]
    p = []
    if manifest.get("status") != "passed":
        p.append("manifest status is %r" % manifest.get("status"))
    if raw_rows != manifest["rows_total"] or raw_rows != len(passed) + len(manifest["quarantined"]):
        p.append("raw has %d rows, Validate counted %d (passed %d + quarantined %d)"
                 % (raw_rows, manifest["rows_total"], len(passed), len(manifest["quarantined"])))
    if not (len(passed) == len(trusted) == len(dim)):
        p.append("row counts differ: passed %d, trusted %d, %s %d" % (len(passed), len(trusted), label, len(dim)))
    if not dim:
        p.append("no rows to publish")
    keys = {"manifest": [r[key] for r in passed],
            "trusted": [r.get(key) for r in trusted],
            label: [r.get(key) for r in dim]}
    for name, v in keys.items():
        dup = [k for k, n in Counter(v).items() if n > 1]
        if dup:
            p.append("%s has %d repeated %s values" % (name, len(dup), key))
    if not (set(keys["manifest"]) == set(keys["trusted"]) == set(keys[label])):
        p.append("%s values differ between manifest, trusted and %s" % (key, label))
    p += schema_problems(trusted_tbl, trusted_contract, "trusted")
    p += schema_problems(dim_tbl, dim_contract, label)
    p += null_problems(trusted, trusted_contract, "trusted")
    p += null_problems(dim, dim_contract, label)
    lo, hi = gee_contract["lst_plausible_c"]
    for r in dim:
        lst, score = r.get("lst_mean_c"), r.get("lst_score")
        if lst is None or not lo <= lst <= hi:
            p.append("%s: a lst_mean_c is outside %g-%g" % (label, lo, hi))
        elif score is None or abs(score - expected_lst_score(lst, gee_contract["lst_score_c"])) > 1e-6:
            p.append("%s: a lst_score is not the fixed scale of its lst_mean_c" % label)
    summary = {"raw_rows": raw_rows, "passed": len(passed), "quarantined": len(manifest["quarantined"]),
               "trusted_rows": len(trusted), "%s_rows" % label: len(dim)}
    return p, summary


def run_gee(batch_id):
    source = lake.source_of(batch_id)
    cfg = GEE_SOURCES[source]
    manifest = lake.get_json(lake.quarantine_prefix(batch_id) + "manifest.json")
    raw_rows = len(read_csv(lake.get_bytes(manifest["raw_key"]))[1])
    dim_bytes = lake.get_bytes(lake.staging_key(batch_id, cfg["table"]))
    problems, summary = gee_checks(
        raw_rows, manifest, parquet.read(lake.get_bytes(lake.trusted_key(batch_id))), parquet.read(dim_bytes),
        lake.contract(cfg["trusted"]), lake.contract(cfg["curated"]), lake.contract("gee_lst"), source)
    if problems:
        raise VerifyFailed("; ".join(problems))
    published = lake.curated_key(cfg["table"])
    lake.put_bytes(published, dim_bytes)
    marker = {"batch_id": batch_id, "status": "SUCCEEDED", "table": cfg["table"], "tables": [cfg["table"]],
              "curated_key": published, "source_file_sha256": manifest["source_file_sha256"],
              "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **summary}
    lake.put_json(lake.success_key(batch_id), marker)
    return marker


def published_rows(source):
    key = lake.curated_key(GEE_SOURCES[source]["table"])
    if key not in lake.list_keys(key):
        return []
    return parquet.read(lake.get_bytes(key)).to_pylist()


def run(batch_id):
    if lake.source_of(batch_id) in GEE_SOURCES:
        return run_gee(batch_id)
    if lake.source_of(batch_id) != "happy_home":
        raise ValueError("no verify step for source %r" % lake.source_of(batch_id))
    manifest = lake.get_json(lake.quarantine_prefix(batch_id) + "manifest.json")
    rules = lake.contract("happy_home")
    raw_rows = len(read_workbook(lake.get_bytes(manifest["raw_key"]))[rules["data_sheet"]].rows)
    staging = lake.staging_key(batch_id, TABLE)
    risk_staging = lake.staging_key(batch_id, RISK_TABLE)
    curated_bytes, risk_bytes = lake.get_bytes(staging), lake.get_bytes(risk_staging)
    dim_rows, hh_rows = published_rows("gee_lst"), published_rows("gee_lst_household")
    problems, summary = checks(
        raw_rows, manifest,
        parquet.read(lake.get_bytes(lake.trusted_key(batch_id))), parquet.read(curated_bytes),
        parquet.read(risk_bytes),
        lake.contract("trusted_happy_home"), lake.contract("curated_happy_home_household"),
        lake.contract("curated_happy_home_risk"), dim_rows, lake.contract("gee_lst")["lst_score_c"], hh_rows)
    if problems:
        raise VerifyFailed("; ".join(problems))
    published = lake.curated_key(TABLE)  # both tables pass every check before either is published
    lake.put_bytes(published, curated_bytes)
    lake.put_bytes(lake.curated_key(RISK_TABLE), risk_bytes)
    marker = {"batch_id": batch_id, "status": "SUCCEEDED", "table": TABLE, "tables": [TABLE, RISK_TABLE],
              "curated_key": published, "risk_key": lake.curated_key(RISK_TABLE),
              "source_file_sha256": manifest["source_file_sha256"],
              "lst_batch_ids": sorted({d["batch_id"] for d in dim_rows}),
              "lst_hh_batch_ids": sorted({d["batch_id"] for d in hh_rows}),
              "lst_hh_households": sum(1 for r in parquet.read(risk_bytes).to_pylist() if r["lst_hh_c"] is not None),
              "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **summary}
    lake.put_json(lake.success_key(batch_id), marker)
    return marker


def handler(event, context):
    lake.force_fail(event, "verify")
    marker = run(event["batch_id"])
    return {**event, "verified": True, "success_key": lake.success_key(event["batch_id"]),
            "curated_key": marker["curated_key"]}
