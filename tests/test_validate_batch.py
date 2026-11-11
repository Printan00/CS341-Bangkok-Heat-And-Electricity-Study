"""Batch-level rules (B01-B06) and the per-batch report, on synthetic workbooks."""
import json
import re

import pytest

import happy_home as hh
from xlsx_helper import rezip, xlsx_bytes

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


@pytest.mark.parametrize("settings_rows", [[], [["setting"]], [["setting"], ["GPS_MODE"]]],
                         ids=["empty", "one_column", "one_column_with_rows"])
def test_b01_settings_sheet_without_setting_value_columns_stops_batch(settings_rows):
    data = xlsx_bytes({"Data": [COLS] + [["HH-%06d" % i, "หลังแฟลต"] for i in range(4)], "Settings": settings_rows})
    r = hh.validate(data, contract(), batch_id="t")
    assert r.status == "failed" and "B01" in rule_ids(r.batch_violations) and r.passed is None


GEO = COLS + ["lat", "lon"]


def geo_contract():
    return contract(columns=GEO, lat_column="lat", lon_column="lon", bbox=[13.5, 14.1, 100.3, 100.9],
                    coord_max_decimals=3)


def test_b01_coordinates_with_more_decimals_than_allowed_stop_batch_even_if_settings_say_rounded():
    rows = [["HH-%06d" % i, "หลังแฟลต", 13.734, 100.512] for i in range(4)]
    rows[2][2] = 13.73456  # Settings still say GPS_DECIMALS = 3
    r = hh.validate(book(rows, GEO), geo_contract(), batch_id="t")
    assert r.status == "failed" and "B01" in rule_ids(r.batch_violations) and r.passed is None
    assert "13.73456" not in json.dumps(r.report())


def test_b01_coordinates_within_allowed_decimals_pass():
    rows = [["HH-%06d" % i, "หลังแฟลต", 13.73, 100.5] for i in range(2)] + [
        ["HH-000002", "หลังแฟลต", 13.734000000000002, 100.512],  # binary noise from rounding, still 3 decimals
        ["HH-000003", "หลังแฟลต", None, 14.0]]
    r = hh.validate(book(rows, GEO), geo_contract(), batch_id="t")
    assert "B01" not in rule_ids(r.batch_violations)


def test_b02_missing_sheet_stops_batch():
    r = hh.validate(book(sheets=("Data",)), contract(), batch_id="t")
    assert "B02" in rule_ids(r.batch_violations) and r.status == "failed"


@pytest.mark.parametrize("data", [
    b"",                                                              # empty upload
    "household_code,ชื่อชุมชน\nHH-000001,หลังแฟลต\n".encode(),        # a CSV renamed to .xlsx
    None,                                                             # truncated upload (filled in below)
    "no_workbook",                                                    # zip without xl/workbook.xml
    "broken_xml",                                                     # workbook.xml is not valid XML
    "bad_shared_string",                                              # cell points past the shared strings
    "bad_number",                                                     # number cell holding text
], ids=["empty", "csv", "truncated", "no_workbook", "broken_xml", "bad_shared_string", "bad_number"])
def test_b02_unreadable_file_stops_batch_with_report_and_no_rows(data):
    good = book()
    sheet = "xl/worksheets/sheet1.xml"
    first_cell = lambda body, new: re.sub(rb'<c r="A2"[^>]*?(/>|>.*?</c>)', new, body, count=1)
    sst = b'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="0" uniqueCount="0"/>'
    data = {None: good[: len(good) // 2],
            "no_workbook": rezip(good, edit={"xl/workbook.xml": lambda b: None}),
            "broken_xml": rezip(good, edit={"xl/workbook.xml": lambda b: b"<workbook"}),
            "bad_shared_string": rezip(good, edit={sheet: lambda b: first_cell(b, b'<c r="A2" t="s"><v>7</v></c>')},
                                       add={"xl/sharedStrings.xml": sst}),
            "bad_number": rezip(good, edit={sheet: lambda b: first_cell(b, b'<c r="A2"><v>abc</v></c>')}),
            }.get(data, data)
    r = hh.validate(data, contract(), batch_id="t")
    assert r.status == "failed" and rule_ids(r.batch_violations) == {"B02"}
    assert r.passed is None and r.quarantine is None
    rep = r.report()
    assert rep["status"] == "failed" and rep["batch_rules"][0]["rule_id"] == "B02"
    assert "HH-000001" not in json.dumps(rep, ensure_ascii=False)


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


def test_report_counts_missing_values_in_passed_rows_with_small_counts_hidden():
    cols = COLS + ["roof", "shade"]
    rows = [["HH-%06d" % i, "หลังแฟลต", "สังกะสี", None if i < 2 else "มี"] for i in range(4)]
    rows += [["HH-%06d" % i, "หลังแฟลต", None, "มี"] for i in range(4, 10)]
    c = contract(columns=cols, expected_rows=10, report_missing=["roof", "shade"])
    rep = hh.validate(book(rows, cols), c, batch_id="t").report()
    assert rep["missing_in_passed_rows"] == {"roof": "6", "shade": "<5"}


def test_report_has_no_missing_counts_when_the_batch_stops():
    rows = [["HH-%06d" % i, "หลังแฟลต", "1/2"] for i in range(4)]
    rep = hh.validate(book(rows, COLS + ["บ้านเลขที่"]), contract(report_missing=["ชื่อชุมชน"]), batch_id="t").report()
    assert rep["missing_in_passed_rows"] is None


def test_report_has_totals_and_per_rule_counts_with_no_ids_or_raw_values():
    rows = [["HH-000000", "หลังแฟลต"], ["HH-000001", "ลับมาก"], ["HH-000002", "หลังแฟลต"], ["HH-000003", "หลังแฟลต"]]
    rep = hh.validate(book(rows), contract(), batch_id="t").report()
    assert (rep["rows_in"], rep["rows_passed"], rep["rows_quarantined"]) == (4, 3, 1)
    assert rep["row_rules"]["R03"] == {"severity": "FAIL", "rows": "<5"}
    text = json.dumps(rep, ensure_ascii=False)
    assert "ลับมาก" not in text and "HH-000001" not in text
