"""Happy Home row rules on tiny synthetic tables (no real data)."""
import happy_home as hh
from core import Table

ID = "household_code"
C = {"id_column": ID, "id_pattern": r"^HH-[0-9A-Za-z]{6}$"}


def tbl(ids=True, **cols):
    n = len(next(iter(cols.values())))
    if ids:
        cols = {ID: ["HH-%06d" % i for i in range(n)], **cols}
    header = list(cols)
    return Table(header, [{h: cols[h][i] for h in header} for i in range(n)])


def hit(violations):
    return {(v.rule_id, v.record_id) for v in violations}


def test_r01_rejects_blank_or_malformed_id():
    t = tbl(ids=False, **{ID: ["HH-abc123", None, "XX-1"]})
    assert hit(hh.check_id(t, C)) == {("R01", None), ("R01", "XX-1")}


def test_r02_rejects_every_copy_of_a_duplicated_id():
    t = tbl(ids=False, **{ID: ["HH-aaaaaa", "HH-aaaaaa", "HH-bbbbbb"]})
    assert [v.rule_id for v in hh.check_id(t, C)] == ["R02", "R02"]


def test_r03_maps_known_labels_and_quarantines_unknown_ones():
    c = dict(C, community_column="ชื่อชุมชน",
             community_map={"ชุมชนหลังแฟลต": "หลังแฟลต", "ชุมชยหลังแฟลต": "หลังแฟลต"})
    t = tbl(ชื่อชุมชน=["ชุมชนหลังแฟลต", "ชุมชยหลังแฟลต ", "F"])
    assert hh.map_community(t, c) == ["หลังแฟลต", "หลังแฟลต", None]
    assert hit(hh.check_community(t, c)) == {("R03", "HH-000002")}


def test_r04_rejects_blank_required_field():
    t = tbl(A7=["x", " ", None])
    assert [v.record_id for v in hh.check_required(t, dict(C, required=["A7"]))] == ["HH-000001", "HH-000002"]


def test_r05_rejects_value_outside_options_ignoring_spacing_and_dash():
    c = dict(C, allowed_values={"C1.3": ["ภายใน 1 ปีที่ผ่านมา", "1–2 ปี"]})
    t = tbl(**{"C1.3": ["ภายใน 1 ปี ที่ผ่านมา", "1-2 ปี", "เมื่อวาน", None]})
    assert hit(hh.check_domain(t, c)) == {("R05", "HH-000002")}


def test_r06_flags_must_be_binary_and_match_parent_text():
    t = tbl(**{"Q": ["พัดลม แอร์", "พัดลม", None, "พัดลม"], "Q/พัดลม": [1, 1, 1, 2], "Q/แอร์": [1, 0, 0, 0]})
    assert hit(hh.check_multiselect(t, C)) == {("R06", "HH-000002"), ("R06", "HH-000003")}


def test_r06_flag_set_but_option_missing_from_text_is_rejected():
    t = tbl(**{"Q": ["พัดลม"], "Q/พัดลม": [1], "Q/แอร์": [1]})
    assert hit(hh.check_multiselect(t, C)) == {("R06", "HH-000000")}


def test_r06_option_must_appear_as_a_whole_option_not_inside_another():
    # A19 has both "จักรยาน" and "จักรยานยนต์"; options are separated by spaces and may contain spaces
    t = tbl(**{"Q": ["จักรยานยนต์", "จักรยาน จักรยานยนต์", "อื่น ๆ จักรยาน"],
               "Q/จักรยาน": [1, 1, 1], "Q/จักรยานยนต์": [0, 1, 0], "Q/อื่น ๆ": [0, 0, 1]})
    assert hit(hh.check_multiselect(t, C)) == {("R06", "HH-000000")}


def test_r06_contract_can_split_two_questions_that_share_a_follow_up_label():
    c = dict(C, multiselect_overrides={"P": ["P/ยกพื้น"], "P.1": ["P/ติดกันสาด", "P/อื่น ๆ.1"]})
    t = tbl(**{"P": ["ยกพื้น", None], "P.1": [None, "ติดกันสาด อื่น ๆ"],
               "P/ยกพื้น": [1, 0], "P/ติดกันสาด": [0, 1], "P/อื่น ๆ.1": [0, 1]})
    assert hh.check_multiselect(t, c) == []


def test_r07_grid_text_must_match_hazard_flags():
    t = tbl(**{"ไฟฟ้า": ["น้ำท่วม", "น้ำท่วม ความร้อน", None, "ฝน"],
               "ไฟฟ้า/น้ำท่วม": [1, 1, 0, 0], "ไฟฟ้า/ความร้อน": [0, 0, 0, 0]})
    assert hit(hh.check_grid(t, C)) == {("R07", "HH-000001"), ("R07", "HH-000003")}


def test_r07_grid_columns_are_not_treated_as_multiselect():
    t = tbl(**{"ไฟฟ้า": ["น้ำท่วม"], "ไฟฟ้า/น้ำท่วม": [1], "ไฟฟ้า/ความร้อน": [0]})
    assert hh.check_multiselect(t, C) == []


def test_r08_follow_up_answered_only_when_gate_says_so():
    c = dict(C, skip_logic=[{"gate": "C1.9", "gate_value": "เคย", "follow": "C1.10"}])
    t = tbl(**{"C1.9": ["เคย", "เคย", "ไม่เคย", "ไม่เคย"], "C1.10": ["หน้าบ้าน", None, "หลังบ้าน", None]})
    assert hit(hh.check_skip_logic(t, c)) == {("R08", "HH-000001"), ("R08", "HH-000002")}


def test_r09_interview_month_must_be_in_window():
    c = dict(C, month_column="วันที่สัมภาษณ์", month_min="2026-06", month_max="2026-08")
    t = tbl(วันที่สัมภาษณ์=["2026-07", "2025-07", "July", None])
    assert [v.record_id for v in hh.check_month(t, c)] == ["HH-000001", "HH-000002", "HH-000003"]


BANDS = dict(C, income_column="A7", normal_bill_column="E1.1", summer_bill_column="E1.2",
             income_bands=["low", "mid", "high"], bill_bands=["b0", "b1", "b2"])


def test_w01_lowest_income_with_top_summer_bill_is_warned():
    t = tbl(A7=["low", "low", "mid"], **{"E1.1": ["b0"] * 3, "E1.2": ["b2", "b1", "b2"]})
    assert hit(hh.check_warnings(t, BANDS)) == {("W01", "HH-000000")}


def test_w02_summer_bill_lower_than_normal_is_warned():
    t = tbl(A7=["mid"] * 2, **{"E1.1": ["b2", "b1"], "E1.2": ["b1", "b1"]})
    assert hit(hh.check_warnings(t, BANDS)) == {("W02", "HH-000000")}


def test_w03_coordinates_blank_or_outside_bbox_are_warned():
    c = dict(C, lat_column="lat", lon_column="lon", bbox=[13.5, 14.1, 100.3, 100.9])
    t = tbl(lat=[13.8, None, 1.0], lon=[100.5, 100.5, 100.5])
    assert hit(hh.check_warnings(t, c)) == {("W03", "HH-000001"), ("W03", "HH-000002")}


def test_w04_none_option_together_with_other_option_is_warned():
    c = dict(C, exclusive_none=[{"none": "A13/ไม่มี", "others": ["A13/เด็ก", "A13/ผู้สูงอายุ"]}])
    t = tbl(**{"A13/ไม่มี": [1, 1], "A13/เด็ก": [0, 1], "A13/ผู้สูงอายุ": [0, None]})
    assert hit(hh.check_warnings(t, c)) == {("W04", "HH-000001")}


def test_w05_says_aircon_drives_bill_without_owning_aircon_is_warned():
    c = dict(C, aircon_flag="E2.1/แอร์", aircon_claims={"E2.4": "เครื่องปรับอากาศ"})
    t = tbl(**{"E2.1/แอร์": [1, 0, 0], "E2.4": ["เครื่องปรับอากาศ", "เครื่องปรับอากาศ", "พัดลม"]})
    assert hit(hh.check_warnings(t, c)) == {("W05", "HH-000001")}


def test_w06_never_flooded_but_frequency_answered_is_warned():
    c = dict(C, flood_never={"gate": "C1.1", "value": "ไม่เคย", "follow": "C1.2"})
    t = tbl(**{"C1.1": ["ไม่เคย", "ไม่เคย", "เคย"], "C1.2": ["ทุกปี", None, "ทุกปี"]})
    assert hit(hh.check_warnings(t, c)) == {("W06", "HH-000000")}


def test_w07_community_only_question_answered_by_other_community_is_warned():
    c = dict(C, community_column="ชื่อชุมชน", community_map={"หลังแฟลต": "หลังแฟลต", "มิตร": "มิตรประชา"},
             community_only_question={"column": "B13", "not_applicable": "ไม่เกี่ยวข้อง", "community": "มิตรประชา"})
    t = tbl(ชื่อชุมชน=["หลังแฟลต", "หลังแฟลต", "มิตร", "F"], B13=["ดีขึ้น", "ไม่เกี่ยวข้อง", "ดีขึ้น", "ดีขึ้น"])
    assert hit(hh.check_warnings(t, c)) == {("W07", "HH-000000")}


def test_w09_rows_identical_except_ids_are_warned():
    c = dict(C, id_columns=[ID, "interviewer_code"])
    t = tbl(interviewer_code=["INT-1", "INT-2", "INT-3"], A7=["low", "low", "mid"])
    assert hit(hh.check_warnings(t, c)) == {("W09", "HH-000000"), ("W09", "HH-000001")}


def test_row_checks_run_only_rules_present_in_contract():
    c = dict(C, community_column="ชื่อชุมชน", community_map={"หลังแฟลต": "หลังแฟลต"})
    t = tbl(ids=False, **{ID: ["HH-0", "HH-000001"], "ชื่อชุมชน": ["หลังแฟลต"] * 2})
    assert {v.rule_id for v in hh.row_checks(t, c)} == {"R01"}
