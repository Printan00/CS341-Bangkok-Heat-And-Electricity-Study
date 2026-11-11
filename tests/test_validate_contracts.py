"""The shipped contracts: every column a rule uses must exist, or that rule would silently check nothing."""
import re

import pytest

from core import load_contract

SINGLE = ("id_column", "community_column", "month_column", "income_column", "expense_column",
          "normal_bill_column", "summer_bill_column", "lat_column", "lon_column", "aircon_flag")


def referenced_columns(c):
    refs = [c[k] for k in SINGLE if k in c]
    refs += c.get("required", []) + list(c.get("allowed_values", {})) + c.get("id_columns", [])
    refs += list(c.get("aircon_claims", {})) + list(c.get("score_exceptions", {})) + c.get("report_missing", [])
    for r in c.get("skip_logic", []):
        refs += [r["gate"], r["follow"]]
    for g in c.get("exclusive_none", []):
        refs += [g["none"]] + g["others"]
    if "flood_never" in c:
        refs += [c["flood_never"]["gate"], c["flood_never"]["follow"]]
    if "community_only_question" in c:
        refs.append(c["community_only_question"]["column"])
    for parent, kids in c.get("multiselect_overrides", {}).items():
        refs += [parent] + list(kids)
    for g in c.get("gate_counts", []):
        refs += [g["gate"], g["count"]]
    if "household_size" in c:
        refs += [c["household_size"]["column"]] + c["household_size"]["totals"]
    for m in c.get("member_sums", []):
        refs += [m["total"]] + m["parts"]
    return refs


@pytest.mark.parametrize("source", ["happy_home", "sovi"])
def test_every_column_a_rule_uses_exists_in_the_contract(source):
    c = load_contract(source)
    missing = [col for col in referenced_columns(c) if col not in c["columns"]]
    assert missing == []


def test_every_flood_and_heat_answer_column_of_happy_home_is_checked():
    # D1.1-D3.2 and G1-G6 export as bare "น้ำท่วม", "ความร้อน.3", "ความร้อนจัด" ... with no question number
    c = load_contract("happy_home")
    hazard = [h for h in c["columns"] if re.fullmatch(r"(น้ำท่วม|ความร้อน)(จัด)?(\.\d+)?", h)]
    assert len(hazard) == 20
    assert [h for h in hazard if h not in c["allowed_values"]] == []


@pytest.mark.parametrize("source", ["happy_home", "sovi"])
def test_data_sheet_is_required_and_no_forbidden_column_is_expected(source):
    c = load_contract(source)
    assert c["data_sheet"] in c["required_sheets"]
    assert not set(c["forbidden_columns"]) & set(c["columns"])
