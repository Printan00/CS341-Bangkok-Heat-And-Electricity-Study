"""Validate rules V01-V14 on synthetic households (reports/validation_rules.md)."""
import pytest

from common.xlsx import read_workbook
from hh_factory import C, Q, col, household, town, workbook
from validate.rules import validate


def check(rows, **kw):
    errors, out = validate(read_workbook(workbook(rows, **kw)), C)
    assert errors == []
    return out


def rules(r, level=None):
    return {rule for rule, lv, _ in r.violations if level in (None, lv)}


def test_ordinary_households_pass_clean():
    out = check(town())
    assert [rules(r) for r in out] == [set()] * 10
    assert all(r.usable == {"q1": True, "q2": True, "q3": True} for r in out)
    assert {r.community_key for r in out} == {"คนรักถิ่น", "หลังแฟลต"}


def test_v01_blank_or_repeated_id_fails():
    rows = town(4)
    rows[0][C["id_column"]] = "  "
    rows[2][C["id_column"]] = rows[3][C["id_column"]]
    out = check(rows)
    assert [r.failed for r in out] == [True, False, True, True]  # every copy of a repeated id
    assert all("V01" in rules(r, "FAIL") for r in (out[0], out[2], out[3]))


def test_v02_blank_community_fails_unmapped_warns():
    rows = town(4)
    rows[0][C["community_column"]] = None
    rows[1][C["community_column"]] = "F"
    rows[2][C["community_column"]] = "ชุมนคนรักถิ่น"  # known misspelling in the map
    out = check(rows)
    assert out[0].failed and "V02" in rules(out[0], "FAIL")
    assert not out[1].failed and "V02" in rules(out[1], "WARN")
    assert (out[1].community_key, out[1].community_source) == ("unknown", "unknown")
    assert (out[2].community_key, rules(out[2])) == ("คนรักถิ่น", set())


def test_v03_answer_not_in_questionnaire_counts_as_missing():
    rows = town(3)
    rows[0][col("B4")] = "ฟาง"
    rows[1][col("C2.6")] = "ทุกคนพอๆกัน"  # docx spells "ทุกคนพอ ๆ กัน": spacing only, accepted
    rows[2][col("C2.5", "นอนไม่หลับ")] = 2  # a 0/1 column with 2
    out = check(rows)
    assert "V03" in rules(out[0]) and out[0].usable["q1"] is False  # B4 is a housing core item
    assert rules(out[1]) == set()
    assert "V03" in rules(out[2]) and out[2].usable["q3"] is False  # C2.5 is a heat-impact core item


def test_v04_coordinates_missing_or_outside_bangkok():
    rows = town(3)
    rows[0][C["lat_column"]] = None
    rows[1][C["lat_column"]], rows[1][C["lon_column"]] = 18.79, 98.98  # Chiang Mai
    out = check(rows)
    assert "V04" in rules(out[0], "WARN") and "V04" in rules(out[1], "WARN")
    assert not out[0].failed and not out[1].failed and out[0].coords is None


@pytest.mark.parametrize("value, rule, failed, unbanded", [
    (0, "V05", True, None), ("0", "V05", True, None),
    (3, "V06", False, 3), ("7", "V06", False, 7), ("หลายคน", "V06", False, None),
])
def test_v05_v06_household_size(value, rule, failed, unbanded):
    rows = town(2)
    rows[0][col("A12")] = value
    r = check(rows)[0]
    assert rule in rules(r) and r.failed is failed and r.a12_unbanded == unbanded


def test_v07_interview_stopped_before_b_or_e():
    rows = town(3)
    late = [c for s in ("B", "C", "E") for c in C["mandatory_sections"][s]]
    for c in late:
        rows[0][c] = None
    for c in C["mandatory_sections"]["E"]:
        rows[1][c] = None
    out = check(rows)
    assert "V07" in rules(out[0]) and out[0].usable == {"q1": False, "q2": False, "q3": False}
    assert "V07" in rules(out[1]) and out[1].usable["q2"] is False  # E1.1/E1.2 missing -> V14
    assert out[1].usable["q1"] is True


def test_v08_v09_bill_bands():
    rows = town(3)
    rows[0][col("E1.2")] = "500–1,000 บาท"  # summer below normal
    rows[1][col("E1.3")] = "ไม่เพิ่ม"
    rows[1][col("E1.2")] = "2,001–3,000 บาท"  # "no increase" but a higher band
    rows[2][col("E1.3")] = "ไม่เพิ่ม"  # same band: fine
    out = check(rows)
    assert "V08" in rules(out[0]) and "V09" in rules(out[1]) and rules(out[2]) == set()


def test_v10_implausible_burden():
    rows = town(2)
    rows[0][col("A7")] = "ต่ำกว่า 5,000 บาท"
    rows[0][col("E1.2")] = "มากกว่า 3,000 บาท"  # 3,001 / 5,000 = 60%
    rows[1][col("A7")] = "ต่ำกว่า 5,000 บาท"
    rows[1][col("E1.2")] = "2,001–3,000 บาท"  # 2,001 / 5,000 = 40%: not flagged
    out = check(rows)
    assert "V10" in rules(out[0]) and "V10" not in rules(out[1])


def test_v11_aircon_used_but_not_owned():
    rows = town(2)
    rows[0][col("C2.7", "เปิดแอร์")] = 1
    out = check(rows)
    assert "V11" in rules(out[0])
    rows[0][col("E2.1", "เครื่องปรับอากาศ")] = 1
    assert "V11" not in rules(check(rows)[0])


def test_v12_none_with_other_options():
    rows = town(2)
    rows[0][col("A13", "ไม่มี")] = 1  # factory already ticks ผู้สูงอายุ
    rows[1][col("A13", "ไม่มี")], rows[1][col("A13", "ผู้สูงอายุ")] = 1, 0
    out = check(rows)
    assert "V12" in rules(out[0]) and "V12" not in rules(out[1])


def test_v13_never_improved_but_lists_improvements():
    rows = town(2)
    for lab, o in Q["C2.8_detail"]["options"].items():
        rows[0][o["column"]] = 1 if lab == "ปลูกต้นไม้" else 0
    out = check(rows)
    assert "V13" in rules(out[0]) and "V13" not in rules(out[1])


def test_v13_ignores_the_flood_improvement_columns():
    # C1.11 (flood) uses the same label without ".1"; it must not trigger the heat rule
    flood = "ถ้าเคย ได้ปรับปรุงอะไรบ้าง/ยกพื้น"
    rows = town(2)
    rows[0][flood] = 1
    out = check(rows, header=list(dict.fromkeys(list(rows[0]) + [flood])))
    assert "V13" not in rules(out[0])


@pytest.mark.parametrize("code, off", [
    ("A7", {"q2", "q3"}), ("E1.1", {"q2", "q3"}), ("C2.1", {"q1", "q3"}), ("A14", {"q1", "q3"}),
])
def test_v14_missing_core_item_turns_off_only_its_questions(code, off):
    rows = town(2)
    rows[0][col(code)] = None
    r = check(rows)[0]
    assert "V14" in rules(r) and not r.failed
    assert {q for q, ok in r.usable.items() if not ok} == off


def test_v14_multi_select_core_blank():
    rows = town(2)
    for o in Q["C2.7"]["options"].values():
        rows[0][o["column"]] = None
    r = check(rows)[0]
    assert "V14" in rules(r) and r.usable == {"q1": False, "q2": True, "q3": False}


def test_d5_suggestion_for_unmapped_row_near_one_community():
    rows = town(8)
    near_a = household(99, "F", (13.8805, 100.580))  # ~55 m from community A, ~1 km from B
    far = household(98, "1", (13.95, 100.70))  # far from both
    out = check(rows + [near_a, far])
    assert out[-2].community_suggested == "คนรักถิ่น" and out[-2].community_key == "unknown"
    assert out[-1].community_suggested is None


def test_t04_mapped_row_sitting_in_other_community_warns():
    rows = town(8)
    rows.append(household(99, "ชุมชนหลังแฟลต", (13.8805, 100.580)))  # labelled B, sits in A
    r = check(rows)[-1]
    assert r.community_key == "หลังแฟลต" and "V02" in rules(r, "WARN") and not r.failed


def test_batch_errors_stop_the_file():
    header = [h for h in household() if h != col("A7")]
    errors, rows = validate(read_workbook(workbook(town(2), header=header)), C)
    assert rows == [] and "ไม่พบคอลัมน์" in errors[0]
    errors, _ = validate(read_workbook(workbook([])), C)
    assert errors == ["ไม่มีแถวข้อมูล"]
    errors, _ = validate(read_workbook(workbook(town(2), sheet="Sheet1")), C)
    assert errors == ["ไม่พบชีต Data"]
