"""The Lambda entry point: reads raw/ from S3, writes quarantine/, returns `valid` for Step Functions."""
import csv
import io
import json

import pytest
from xlsx_helper import xlsx_bytes

import handler

HH_CONTRACT = {
    "data_sheet": "Data", "required_sheets": ["Data"], "columns": ["household_code", "ชื่อชุมชน"],
    "forbidden_columns": ["บ้านเลขที่"], "max_quarantine_rate": 0.5,
    "id_column": "household_code", "id_pattern": r"^HH-\d{6}$",
    "community_column": "ชื่อชุมชน", "community_map": {"หลังแฟลต": "หลังแฟลต"},
}


class FakeS3:
    """Just the three S3 calls the handler uses, backed by a dict."""

    def __init__(self, objects):
        self.objects = dict(objects)

    def list_objects_v2(self, Bucket, Prefix):
        return {"Contents": [{"Key": k} for k in sorted(self.objects) if k.startswith(Prefix)]}

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.objects[Key] = Body if isinstance(Body, bytes) else Body.encode("utf-8")


RAW = "raw/happy_home/b1/hh.xlsx"
OUT = "quarantine/happy_home/b1/"


def run(rows, header=("household_code", "ชื่อชุมชน"), event=None):
    s3 = FakeS3({RAW: xlsx_bytes({"Data": [list(header)] + rows})})
    result = handler.run(event or {"batch_id": "b1"}, s3=s3, bucket="lake",
                         contracts={"happy_home": HH_CONTRACT})
    return result, s3


def test_clean_batch_is_valid_and_writes_report_and_manifest():
    result, s3 = run([["HH-000001", "หลังแฟลต"], ["HH-000002", "หลังแฟลต"]])
    assert result["valid"] is True and result["batch_id"] == "b1"
    [summary] = result["validation"]
    assert summary["source"] == "happy_home" and summary["raw_key"] == RAW
    assert (summary["rows_in"], summary["rows_passed"], summary["rows_quarantined"]) == (2, 2, 0)
    manifest = json.loads(s3.objects[OUT + "manifest.json"])
    assert [p["id"] for p in manifest["passed"]] == ["HH-000001", "HH-000002"]
    assert json.loads(s3.objects[OUT + "dq_report.json"])["status"] == "passed"


def test_bad_row_is_written_to_quarantine_with_its_reasons():
    result, s3 = run([["HH-000001", "หลังแฟลต"], ["HH-000002", "F"]])
    assert result["valid"] is True
    quarantined = [json.loads(line) for line in s3.objects[OUT + "rows.jsonl"].decode().splitlines()]
    assert [(q["household_code"], q["rule_ids"]) for q in quarantined] == [("HH-000002", "R03")]
    violations = list(csv.DictReader(io.StringIO(s3.objects[OUT + "violations.csv"].decode("utf-8-sig"))))
    assert [(v["rule_id"], v["record_id"], v["source_row"]) for v in violations] == [("R03", "HH-000002", "3")]


def test_privacy_failure_is_invalid_and_keeps_no_rows():
    result, s3 = run([["HH-000001", "หลังแฟลต", "12/3"]], header=("household_code", "ชื่อชุมชน", "บ้านเลขที่"))
    assert result["valid"] is False
    assert s3.objects[OUT + "rows.jsonl"] == b""
    manifest = json.loads(s3.objects[OUT + "manifest.json"])
    assert manifest["status"] == "failed" and manifest["passed"] == [] and manifest["quarantined"] == []
    assert b"12/3" not in b"".join(v for k, v in s3.objects.items() if k.startswith(OUT))


def test_rerun_that_stops_at_batch_level_replaces_the_previous_run_outputs():
    s3 = FakeS3({RAW: xlsx_bytes({"Data": [["household_code", "ชื่อชุมชน"], ["HH-000001", "หลังแฟลต"]]})})
    first = handler.run({"batch_id": "b1"}, s3=s3, bucket="lake", contracts={"happy_home": HH_CONTRACT})
    assert first["valid"] is True
    assert json.loads(s3.objects[OUT + "manifest.json"])["status"] == "passed"
    stricter = dict(HH_CONTRACT, columns=HH_CONTRACT["columns"] + ["new_column"])  # contract changed later
    second = handler.run({"batch_id": "b1"}, s3=s3, bucket="lake", contracts={"happy_home": stricter})
    assert second["valid"] is False
    manifest = json.loads(s3.objects[OUT + "manifest.json"])
    assert manifest["status"] == "failed" and manifest["passed"] == []
    assert s3.objects[OUT + "rows.jsonl"] == b""
    violations = list(csv.DictReader(io.StringIO(s3.objects[OUT + "violations.csv"].decode("utf-8-sig"))))
    assert [v["rule_id"] for v in violations] == ["B03"]


def test_unreadable_file_is_invalid_with_a_b02_report():
    s3 = FakeS3({RAW: b"this is not an xlsx file"})
    result = handler.run({"batch_id": "b1"}, s3=s3, bucket="lake", contracts={"happy_home": HH_CONTRACT})
    assert result["valid"] is False
    assert json.loads(s3.objects[OUT + "manifest.json"])["passed"] == []
    report = json.loads(s3.objects[OUT + "dq_report.json"])
    assert [b["rule_id"] for b in report["batch_rules"]] == ["B02"]


def test_ingest_layout_only_the_batch_source_is_checked():
    # scripts/ingest.py: raw/<source>/<source>-<sha12>/<file>.xlsx + _manifest.json, one source per batch
    hh_key = "raw/happy_home/happy_home-aaa/hh.xlsx"
    s3 = FakeS3({
        hh_key: xlsx_bytes({"Data": [["household_code", "ชื่อชุมชน"], ["HH-000001", "หลังแฟลต"]]}),
        "raw/happy_home/happy_home-aaa/_manifest.json": b"{}",
        "raw/sovi/sovi-bbb/sv.xlsx": b"not read",
    })
    result = handler.run({"batch_id": "happy_home-aaa"}, s3=s3, bucket="lake",
                         contracts={"happy_home": HH_CONTRACT, "sovi": {}})
    assert result["valid"] is True
    assert [(v["source"], v["raw_key"]) for v in result["validation"]] == [("happy_home", hh_key)]
    assert "quarantine/happy_home/happy_home-aaa/manifest.json" in s3.objects


def test_missing_raw_file_raises_so_the_execution_fails_loudly():
    with pytest.raises(FileNotFoundError):
        handler.run({"batch_id": "nope"}, s3=FakeS3({}), bucket="lake", contracts={"happy_home": HH_CONTRACT})


def test_fail_at_hook_from_the_stub_still_works():
    with pytest.raises(RuntimeError):
        handler.handler({"batch_id": "b1", "fail_at": "validate"}, None)
