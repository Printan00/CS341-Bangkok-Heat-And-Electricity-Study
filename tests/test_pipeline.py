"""Validate -> Transform -> Integrate -> Verify through an in-memory S3, on synthetic households."""
import csv
import io
import json

import pytest

from check_batch.handler import handler as check_batch
from common import lake, parquet
from hh_factory import C, col, household, town, workbook
from integrate.handler import handler as integrate, ranks, risk
from transform.handler import handler as transform
from validate.handler import handler as validate
from verify.handler import VerifyFailed, handler as verify

BATCH = "happy_home-0123456789ab"
Q = "quarantine/happy_home/%s/" % BATCH


def ingest(s3, rows=None, data=None, batch=BATCH):
    s3.objects["raw/%s/%s/survey.xlsx" % (lake.source_of(batch), batch)] = data or workbook(rows)
    s3.objects["raw/%s/%s/_manifest.json" % (lake.source_of(batch), batch)] = b"{}"  # ignored


def run_all(s3, rows):
    ingest(s3, rows)
    ev = {"batch_id": BATCH}
    for step in (validate, transform, integrate, verify):
        ev = step(ev, None)
    return ev


def table(s3, key):
    return parquet.read(s3.objects[key]).to_pylist()


# ---------- Validate (#19) ----------

def test_validate_writes_report_and_quarantine(s3):
    rows = town(6)
    rows[0][C["id_column"]] = None  # V01 FAIL
    rows[1][col("A12")] = 0  # V05 FAIL
    rows[2][col("C2.7", "เปิดแอร์")] = 1  # V11 WARN
    ingest(s3, rows)
    out = validate({"batch_id": BATCH}, None)
    assert (out["valid"], out["rows_passed"], out["rows_quarantined"]) == (True, 4, 2)

    rep = json.loads(s3.objects[Q + "dq_report.json"])
    assert (rep["rows_total"], rep["rows_passed"], rep["rows_quarantined"]) == (6, 4, 2)
    assert rep["rules"] == {"V01": {"FAIL": "<5"}, "V05": {"FAIL": "<5"}, "V11": {"WARN": "<5"}}

    man = json.loads(s3.objects[Q + "manifest.json"])
    assert man["status"] == "passed" and len(man["passed"]) == 4
    assert {q["rules"][0] for q in man["quarantined"]} == {"V01", "V05"}
    flagged = [p for p in man["passed"] if p["dq_flags"]]
    assert [p["dq_flags"] for p in flagged] == [["V11"]]

    lines = s3.objects[Q + "rows.jsonl"].decode().splitlines()
    assert len(lines) == 2 and "values" in json.loads(lines[0])
    viol = list(csv.DictReader(io.StringIO(s3.objects[Q + "violations.csv"].decode("utf-8-sig"))))
    assert {v["rule"] for v in viol} == {"V01", "V05", "V11"}


def test_validate_rerun_overwrites_same_files(s3):
    ingest(s3, town(4))
    validate({"batch_id": BATCH}, None)
    first = dict(s3.objects)
    validate({"batch_id": BATCH}, None)
    assert set(s3.objects) == set(first)


def test_unreadable_file_is_reported_not_crashed(s3):
    ingest(s3, data=b"not a zip")
    out = validate({"batch_id": BATCH}, None)
    rep = json.loads(s3.objects[Q + "dq_report.json"])
    assert out["valid"] is False and "เปิดไฟล์ .xlsx ไม่ได้" in rep["batch_errors"][0]
    assert json.loads(s3.objects[Q + "manifest.json"])["status"] == "failed"


def test_sovi_stops_at_validate_until_it_has_rules(s3):
    batch = "sovi-0123456789ab"
    ingest(s3, town(2), batch=batch)
    out = validate({"batch_id": batch}, None)
    assert out["valid"] is False
    assert "sovi" in json.loads(s3.objects["quarantine/sovi/%s/dq_report.json" % batch])["batch_errors"][0]


def test_every_row_quarantined_means_not_valid(s3):
    rows = town(2)
    for r in rows:
        r[col("A12")] = 0
    ingest(s3, rows)
    assert validate({"batch_id": BATCH}, None)["valid"] is False


def test_missing_raw_file_fails_the_step(s3):
    with pytest.raises(FileNotFoundError):
        validate({"batch_id": BATCH}, None)


def test_fail_at_hook(s3):
    with pytest.raises(RuntimeError):
        validate({"batch_id": BATCH, "fail_at": "validate"}, None)


# ---------- Transform (#20) ----------

def test_trusted_has_contract_schema_and_no_private_columns(s3):
    run_all(s3, town(4))
    tbl = parquet.read(s3.objects[lake.trusted_key(BATCH)])
    contract = lake.contract("trusted_happy_home")
    assert tbl.schema.names == [c["name"] for c in contract["columns"]]
    assert tbl.schema.equals(parquet.schema(contract))
    rows = tbl.to_pylist()
    for forbidden in contract["forbidden_columns"]:
        assert forbidden not in tbl.schema.names
    # no coordinate or community-name text anywhere in the values either
    text = json.dumps(rows, ensure_ascii=False)
    assert "13.88" not in text and "100.58" not in text and "ชุมชนคนรักถิ่น" not in text


def test_transform_rules_t01_to_t11(s3):
    rows = town(4)
    rows[0][col("A7")] = "5,001-10,000 บาท"  # hyphen instead of en dash (T01)
    rows[0][col("E1.2")] = "1,001–2,000 บาท"  # 1,001/10,000 .. 2,000/5,001 -> 10%-40% = high (T07)
    rows[0][col("B6")] = "ไม่แน่ใจ"  # unsure -> null in _clean (T02)
    rows[1][col("A12")] = 7  # -> "6+" (T03)
    rows[2][col("B4")] = "สังกะสี/เมทัลชีท"
    rows[2][col("B6")] = rows[2][col("B7")] = "ไม่มี"
    rows[2][col("B8")] = "ไม่ดี"
    rows[2][col("B9")] = "ไม่มีเลย"  # housing 5/5 (T09)
    rows[3][col("C2.1")] = "ร้อนมากทุกวัน"
    rows[3][col("D1.1H")], rows[3][col("D2.1H")], rows[3][col("D2.2H")] = "มาก", "เคย", "มาก"
    for lab in ("อยู่ในบ้านไม่สบาย", "ปวดหัว/อ่อนเพลีย", "ทำงานลำบาก", "เด็กเรียนหนังสือลำบาก", "ค่าไฟเพิ่ม"):
        rows[3][col("C2.5", lab)] = 1  # ค่าไฟเพิ่ม does not count -> 3 + 5 + 2 + 1 + 2 = 13 (T10)
    rows[3][col("A14")] = "เช่า"
    rows[3][col("A10")] = "ไม่มี"
    rows[3][col("G8")] = "ไม่มี"
    rows[3][col("C2.7", "ไม่มีวิธีรับมือ")] = 1
    rows[3][col("B12", "ไม่มีงบประมาณ")] = 1  # + elderly from the factory -> coping 6/6
    run_all(s3, rows)
    t = {r["source_row"]: r for r in table(s3, lake.trusted_key(BATCH))}
    a, b, c, d = (t[i] for i in (2, 3, 4, 5))

    assert a["a7_income_band"] == "5,001–10,000 บาท" and a["a7_income_band_clean"] == "5,001–10,000 บาท"
    assert (a["income_ord"], a["income_min"], a["income_max"]) == (2, 5001, 10000)
    assert a["burden_min"] == pytest.approx(0.1001) and a["burden_max"] == pytest.approx(2000 / 5001)
    assert a["burden_class"] == "high"
    assert a["b6_ceiling"] == "ไม่แน่ใจ" and a["b6_ceiling_clean"] is None
    assert a["housing_items_answered"] == 4

    assert b["a12_household_size"] == "7" and b["household_size_band"] == "6+"
    assert c["housing_heat_score"] == 5
    assert d["heat_impact_score"] == 13 and d["heat_impact_level"] == "high"
    assert d["coping_limit_score"] == 6 and d["coping_limited"] is True
    assert a["has_aircon"] is False
    assert a["source_dataset"] == "happy_home" and a["batch_id"] == BATCH and len(a["source_file_sha256"]) == 64


def test_housing_score_needs_four_clear_answers(s3):
    rows = town(2)
    rows[0][col("B6")] = rows[0][col("B7")] = "ไม่แน่ใจ"
    run_all(s3, rows)
    r = table(s3, lake.trusted_key(BATCH))[0]
    assert (r["housing_heat_score"], r["housing_items_answered"]) == (None, 3)


def test_transform_refuses_a_failed_batch(s3):
    ingest(s3, data=b"broken")
    validate({"batch_id": BATCH}, None)
    with pytest.raises(ValueError, match="did not pass"):
        transform({"batch_id": BATCH}, None)
    assert lake.trusted_key(BATCH) not in s3.objects


# ---------- Integrate (T13) ----------

def test_risk_score_weights():
    row = {"usable_q3": True, "heat_impact_score": 13, "housing_heat_score": 5,
           "burden_class": "possibly_high", "coping_limit_score": 3}
    assert risk(row, 2) == pytest.approx(1 + 1 + 1 + 0.5)
    assert risk(row, 1) == pytest.approx(1 + 1 + 0.5 + 0.5)
    assert risk({**row, "usable_q3": False}, 2) is None
    assert risk({**row, "housing_heat_score": None}, 2) is None


def test_ranks_share_ties():
    assert ranks([0.5, 2.0, None, 2.0, 1.0]) == [4, 1, None, 1, 3]


# ---------- Verify (#22) ----------

def test_verify_publishes_and_writes_success(s3):
    out = run_all(s3, town(6))
    marker = json.loads(s3.objects[lake.success_key(BATCH)])
    assert out["verified"] is True and marker["status"] == "SUCCEEDED"
    assert (marker["raw_rows"], marker["trusted_rows"], marker["curated_rows"]) == (6, 6, 6)
    assert s3.objects[lake.curated_key("happy_home_household")] == \
        s3.objects[lake.staging_key(BATCH, "happy_home_household")]
    cur = table(s3, lake.curated_key("happy_home_household"))
    assert [c["name"] for c in lake.contract("curated_happy_home_household")["columns"]] == list(cur[0])


def _until_integrate(s3, rows):
    ingest(s3, rows)
    ev = {"batch_id": BATCH}
    for step in (validate, transform, integrate):
        ev = step(ev, None)


def test_verify_fails_on_lost_row_and_publishes_nothing(s3):
    _until_integrate(s3, town(4))
    key = lake.staging_key(BATCH, "happy_home_household")
    tbl = parquet.read(s3.objects[key])
    s3.objects[key] = _parquet(tbl.slice(0, 3))  # one household lost between trusted and curated
    with pytest.raises(VerifyFailed, match="row counts differ"):
        verify({"batch_id": BATCH}, None)
    assert lake.curated_key("happy_home_household") not in s3.objects
    assert lake.success_key(BATCH) not in s3.objects


def test_verify_fails_on_extra_column(s3):
    import pyarrow as pa

    _until_integrate(s3, town(4))
    key = lake.trusted_key(BATCH)
    tbl = parquet.read(s3.objects[key])
    s3.objects[key] = _parquet(tbl.append_column("latitude", pa.array([13.88] * tbl.num_rows)))
    with pytest.raises(VerifyFailed, match="forbidden columns"):
        verify({"batch_id": BATCH}, None)


def test_verify_fails_when_raw_count_disagrees(s3):
    _until_integrate(s3, town(4))
    s3.objects["raw/happy_home/%s/survey.xlsx" % BATCH] = workbook(town(5))  # raw changed after Validate
    with pytest.raises(VerifyFailed, match="raw has 5 rows"):
        verify({"batch_id": BATCH}, None)


def test_rerun_does_not_add_rows(s3):
    run_all(s3, town(4))
    ev = {"batch_id": BATCH}
    for step in (validate, transform, integrate, verify):
        ev = step(ev, None)
    assert len(table(s3, lake.curated_key("happy_home_household"))) == 4


# ---------- CheckBatch (#21) ----------

def test_check_batch_new_batch_runs(s3):
    ingest(s3, town(2))
    assert check_batch({"batch_id": BATCH}, None)["already_done"] is False


def test_check_batch_skips_a_published_batch(s3):
    run_all(s3, town(3))
    assert check_batch({"batch_id": BATCH}, None)["already_done"] is True
    assert check_batch({"batch_id": "happy_home-ffffffffffff"}, None)["already_done"] is False


def test_force_reruns_a_published_batch_without_duplicates(s3):
    run_all(s3, town(3))
    assert check_batch({"batch_id": BATCH, "force": True}, None)["already_done"] is False
    assert check_batch({"batch_id": BATCH, "force": "yes"}, None)["already_done"] is True  # only true counts
    run_all(s3, town(3))
    assert len(table(s3, lake.curated_key("happy_home_household"))) == 3


def test_check_batch_ignores_a_marker_that_is_not_success(s3):
    s3.objects[lake.success_key(BATCH)] = json.dumps({"batch_id": "other", "status": "SUCCEEDED"}).encode()
    assert check_batch({"batch_id": BATCH}, None)["already_done"] is False


def test_failed_half_way_then_rerun_completes_without_duplicates(s3):
    _until_integrate(s3, town(4))  # stopped before Verify: no marker yet
    assert check_batch({"batch_id": BATCH}, None)["already_done"] is False
    run_all(s3, town(4))
    assert check_batch({"batch_id": BATCH}, None)["already_done"] is True
    assert len(table(s3, lake.curated_key("happy_home_household"))) == 4


def _parquet(tbl):
    import pyarrow.parquet as pq

    buf = io.BytesIO()
    pq.write_table(tbl, buf)
    return buf.getvalue()
