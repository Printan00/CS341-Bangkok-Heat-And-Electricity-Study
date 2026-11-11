"""Done criteria of #19 on the real sample files: deliberately broken copies must land in quarantine.

The survey files are never in the repo. These tests run only when BHES_SAMPLE_DIR points to the
folder that holds the two anonymised .xlsx files; otherwise they are skipped.
"""
import io
import os
from pathlib import Path

import openpyxl
import pytest

import happy_home
import sovi
import xlsx
from core import load_contract

SAMPLE = os.environ.get("BHES_SAMPLE_DIR")
pytestmark = pytest.mark.skipif(not SAMPLE, reason="set BHES_SAMPLE_DIR to run on the real sample files")

HH_FILE = "ThaiCI_Household_Questionaire_anonymized.xlsx"
SV_FILE = "SOVI_Survey_Questionaire_anonymized.xlsx"


def raw(name):
    return (Path(SAMPLE) / name).read_bytes()


def broken_copy(name, sheet, edits):
    """edits: [(excel row, header name, new value)] or [(None, new header, fill value)] to add a column."""
    wb = openpyxl.load_workbook(io.BytesIO(raw(name)))
    ws = wb[sheet]
    header = [c.value for c in ws[1]]
    for row, col, value in edits:
        if row is None:
            ws.cell(1, ws.max_column + 1, col)
            for r in range(2, ws.max_row + 1):
                ws.cell(r, ws.max_column, value)
        else:
            ws.cell(row, header.index(col) + 1, value)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def rules_of(result, record_id, id_col):
    return {r for q in result.quarantine if q[id_col] == record_id for r in q["rule_ids"].split(";")}


def test_reader_header_matches_contract_for_both_files():
    assert xlsx.read_workbook(raw(HH_FILE))["Data"].header == load_contract("happy_home")["columns"]
    assert xlsx.read_workbook(raw(SV_FILE))["ใส่ค่าคะแนน"].header == load_contract("sovi")["columns"]


def test_happy_home_sample_matches_documented_counts():
    rep = happy_home.validate(raw(HH_FILE), batch_id="sample").report()
    assert rep["status"] == "passed"
    assert (rep["rows_in"], rep["rows_passed"], rep["rows_quarantined"], rep["rows_with_warnings"]) == (88, 81, 7, 10)
    assert set(rep["row_rules"]) >= {"R03"} and not any(k.startswith("R") and k != "R03" for k in rep["row_rules"])


def test_happy_home_heat_impact_columns_are_checked_against_the_questionnaire():
    # D1.1 / G6 columns lost their question number in the export ("ความร้อน", "ความร้อน.8") but are still checked
    base = happy_home.validate(raw(HH_FILE), batch_id="b")
    row_of = {r["household_code"]: i + 2 for i, r in enumerate(xlsx.read_workbook(raw(HH_FILE))["Data"].rows)}
    a, b = base.passed[0]["household_code"], base.passed[1]["household_code"]
    r = happy_home.validate(broken_copy(HH_FILE, "Data", [(row_of[a], "ความร้อน", "รุนแรงสุด"),
                                                          (row_of[b], "ความร้อน.8", "แมว")]), batch_id="b")
    assert rules_of(r, a, "household_code") == {"R05"}
    assert rules_of(r, b, "household_code") == {"R05"}


def test_happy_home_report_counts_missing_values_of_analysis_variables():
    rep = happy_home.validate(raw(HH_FILE), batch_id="b").report()
    missing = rep["missing_in_passed_rows"]
    assert set(missing) == set(load_contract("happy_home")["report_missing"])
    assert missing["ความร้อน"] == "0" and missing["B4. วัสดุหลังคาหลัก"] == "0"


def test_happy_home_broken_rows_go_to_quarantine():
    c = load_contract("happy_home")
    base = happy_home.validate(raw(HH_FILE), batch_id="b")
    good = base.passed[:3]
    row_of = {r["household_code"]: i + 2 for i, r in enumerate(xlsx.read_workbook(raw(HH_FILE))["Data"].rows)}
    a, b, d = (g["household_code"] for g in good)
    data = broken_copy(HH_FILE, "Data", [
        (row_of[a], c["income_column"], "ล้านบาท"),   # not a questionnaire option -> R05
        (row_of[b], c["aircon_flag"], 2),            # multi-select flag not 0/1 -> R06
        (row_of[d], "household_code", a),            # duplicate id -> R02 on both copies
    ])
    r = happy_home.validate(data, batch_id="b")
    assert rules_of(r, a, "household_code") == {"R05", "R02"}
    assert rules_of(r, b, "household_code") == {"R06"}
    assert len(r.quarantine) == 7 + 3
    # 10 of 88 rows (11%) is under the 15% batch threshold, so the batch still passes
    assert r.status == "passed" and "B06" not in {v.rule_id for v in r.batch_violations}


def test_happy_home_leaked_identifier_column_stops_batch_without_rows():
    r = happy_home.validate(broken_copy(HH_FILE, "Data", [(None, "บ้านเลขที่", "x")]), batch_id="b")
    assert r.status == "failed" and "B01" in {v.rule_id for v in r.batch_violations}
    assert r.passed is None and r.quarantine is None


def test_sovi_sample_passes_and_broken_rows_go_to_quarantine():
    base = sovi.validate(raw(SV_FILE), batch_id="s")
    assert base.status == "passed" and (len(base.passed), len(base.quarantine)) == (500, 0)
    income = next(iter(load_contract("sovi")["allowed_values"]))
    first, second = base.passed[0]["respondent_id"], base.passed[1]["respondent_id"]
    r = sovi.validate(broken_copy(SV_FILE, "ใส่ค่าคะแนน", [(2, income, "ล้านบาท"), (3, "v5.ประเภทครัวเรือน", 9)]),
                      batch_id="s")
    assert rules_of(r, first, "respondent_id") == {"S03"}
    assert rules_of(r, second, "respondent_id") == {"S06"}
    assert len(r.quarantine) == 2 and r.status == "passed"


def test_sovi_debt_and_savings_are_checked_and_export_label_for_savings_is_accepted():
    c = load_contract("sovi")
    debt = next(k for k in c["allowed_values"] if k.startswith("17."))
    saving = next(k for k in c["allowed_values"] if k.startswith("18."))
    base = sovi.validate(raw(SV_FILE), batch_id="s")
    first, second, third = (base.passed[i]["respondent_id"] for i in range(3))
    r = sovi.validate(broken_copy(SV_FILE, "ใส่ค่าคะแนน", [(2, debt, "ล้านล้าน"), (3, saving, "รวยมาก"),
                                                           (4, saving, "มีเงินออม")]), batch_id="s")
    assert rules_of(r, first, "respondent_id") == {"S03"}
    assert rules_of(r, second, "respondent_id") == {"S03"}
    assert rules_of(r, third, "respondent_id") == set()
    assert set(r.report()["missing_in_passed_rows"]) == set(c["report_missing"])
