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


RAW = "raw/happy_home/batch_id=b1/hh.xlsx"
OUT = "quarantine/happy_home/batch_id=b1/"


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


def test_privacy_failure_is_invalid_and_writes_only_the_report():
    result, s3 = run([["HH-000001", "หลังแฟลต", "12/3"]], header=("household_code", "ชื่อชุมชน", "บ้านเลขที่"))
    assert result["valid"] is False
    written = sorted(k for k in s3.objects if k.startswith("quarantine/"))
    assert written == [OUT + "dq_report.json"]


def test_missing_raw_file_raises_so_the_execution_fails_loudly():
    with pytest.raises(FileNotFoundError):
        handler.run({"batch_id": "nope"}, s3=FakeS3({}), bucket="lake", contracts={"happy_home": HH_CONTRACT})


def test_fail_at_hook_from_the_stub_still_works():
    with pytest.raises(RuntimeError):
        handler.handler({"batch_id": "b1", "fail_at": "validate"}, None)
