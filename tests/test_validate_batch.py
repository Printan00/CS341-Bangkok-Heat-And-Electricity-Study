"""Batch-level rules (B01-B06) and the per-batch report, on synthetic workbooks."""
import json

import happy_home as hh
from xlsx_helper import xlsx_bytes

COLS = ["household_code", "ชื่อชุมชน"]


def contract(**over):
    c = {
        "data_sheet": "Data", "required_sheets": ["Data", "Settings"], "columns": COLS,
        "forbidden_columns": ["บ้านเลขที่"], "settings_sheet": "Settings",
        "settings_rules": {"GPS_MODE": {"eq": "round"}, "GPS_DECIMALS": {"max": 3}},
        "expected_rows": 4, "max_quarantine_rate": 0.30,
        "id_column": "household_code", "id_pattern": r"^HH-[0-9a-z]{6}$",
        "community_column": "ชื่อชุมชน", "community_map": {"หลังแฟลต": "หลังแฟลต"},
    }
    c.update(over)
    return c


def book(rows=None, columns=COLS, settings=None, sheets=("Data", "Settings")):
    rows = rows if rows is not None else [["HH-%06d" % i, "หลังแฟลต"] for i in range(4)]
    settings = settings or {"GPS_MODE": "round", "GPS_DECIMALS": 3}
    content = {}
    if "Data" in sheets:
        content["Data"] = [columns] + rows
    if "Settings" in sheets:
        content["Settings"] = [["setting", "value"]] + [list(kv) for kv in settings.items()]
    return xlsx_bytes(content)


def rule_ids(violations):
    return {v.rule_id for v in violations}


def test_clean_batch_passes_every_row():
    r = hh.validate(book(), contract(), batch_id="t")
    assert r.status == "passed" and len(r.passed) == 4 and r.quarantine == []
    assert len(r.sha256) == 64


def test_b01_forbidden_column_stops_batch_and_keeps_no_rows():
    rows = [["HH-%06d" % i, "หลังแฟลต", "1/2"] for i in range(4)]
    r = hh.validate(book(rows, COLS + ["บ้านเลขที่"]), contract(), batch_id="t")
    assert r.status == "failed" and "B01" in rule_ids(r.batch_violations)
    assert r.passed is None and r.quarantine is None


def test_b01_gps_precision_above_contract_stops_batch():
    r = hh.validate(book(settings={"GPS_MODE": "round", "GPS_DECIMALS": 5}), contract(), batch_id="t")
    assert "B01" in rule_ids(r.batch_violations) and r.passed is None


def test_b02_missing_sheet_stops_batch():
    r = hh.validate(book(sheets=("Data",)), contract(), batch_id="t")
    assert "B02" in rule_ids(r.batch_violations) and r.status == "failed"


def test_b03_changed_column_order_stops_batch():
    rows = [["หลังแฟลต", "HH-%06d" % i] for i in range(4)]
    r = hh.validate(book(rows, list(reversed(COLS))), contract(), batch_id="t")
    assert "B03" in rule_ids(r.batch_violations) and r.passed is None


def test_b04_empty_sheet_fails_and_unexpected_count_only_warns():
    assert "B04" in rule_ids(hh.validate(book(rows=[]), contract(), batch_id="t").batch_violations)
    r = hh.validate(book(rows=[["HH-%06d" % i, "หลังแฟลต"] for i in range(3)]), contract(), batch_id="t")
    assert r.status == "passed" and [v.severity for v in r.batch_violations] == ["WARN"]


def test_bad_rows_go_to_quarantine_with_reason_and_good_rows_get_community_key():
    rows = [["HH-000000", "หลังแฟลต"], ["HH-000001", "F"], ["HH-000002", "หลังแฟลต"], ["HH-000003", "หลังแฟลต"]]
    r = hh.validate(book(rows), contract(), batch_id="t")
    assert [(q["household_code"], q["rule_ids"]) for q in r.quarantine] == [("HH-000001", "R03")]
    assert [p["community_key"] for p in r.passed] == ["หลังแฟลต"] * 3


def test_b06_too_many_quarantined_rows_fails_batch():
    rows = [["HH-000000", "F"], ["HH-000001", "F"], ["HH-000002", "หลังแฟลต"], ["HH-000003", "หลังแฟลต"]]
    r = hh.validate(book(rows), contract(), batch_id="t")
    assert r.status == "failed" and "B06" in rule_ids(r.batch_violations)


def test_b06_real_contracts_allow_up_to_15_percent():
    from core import load_contract, quarantine_rate_violation
    for source in ("happy_home", "sovi"):
        rate = load_contract(source)["max_quarantine_rate"]
        assert quarantine_rate_violation(13, 88, rate) is None        # 14.8%
        assert quarantine_rate_violation(14, 88, rate).rule_id == "B06"  # 15.9%


def test_report_has_totals_and_per_rule_counts_with_no_ids_or_raw_values():
    rows = [["HH-000000", "หลังแฟลต"], ["HH-000001", "ลับมาก"], ["HH-000002", "หลังแฟลต"], ["HH-000003", "หลังแฟลต"]]
    rep = hh.validate(book(rows), contract(), batch_id="t").report()
    assert (rep["rows_in"], rep["rows_passed"], rep["rows_quarantined"]) == (4, 3, 1)
    assert rep["row_rules"]["R03"] == {"severity": "FAIL", "rows": "<5"}
    text = json.dumps(rep, ensure_ascii=False)
    assert "ลับมาก" not in text and "HH-000001" not in text
