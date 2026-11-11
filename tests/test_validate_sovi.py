"""SoVI V8 row rules on tiny synthetic tables (no real data)."""
import sovi
from core import Table

ID = "respondent_id"
C = {"id_column": ID, "id_pattern": r"^S\d{4}$"}


def tbl(ids=True, **cols):
    n = len(next(iter(cols.values())))
    if ids:
        cols = {ID: ["S%04d" % i for i in range(n)], **cols}
    header = list(cols)
    return Table(header, [{h: cols[h][i] for h in header} for i in range(n)])


def hit(violations):
    return {(v.rule_id, v.record_id) for v in violations}


def test_s01_rejects_bad_or_duplicated_respondent_id():
    t = tbl(ids=False, **{ID: ["S0001", "S0001", "X9", None]})
    assert hit(sovi.check_id(t, C)) == {("S01", "S0001"), ("S01", "X9"), ("S01", None)}


def test_s02_community_must_be_listed_and_code_prefix_is_split_off():
    c = dict(C, community_column="พื้นที่",
             community_map={"(71) ทรัพย์สินพัฒนา": "ทรัพย์สินพัฒนา", "ราศรีธรรม": "ราศรีธรรม"})
    t = tbl(พื้นที่=["(71) ทรัพย์สินพัฒนา", "ราศรีธรรม", "ชุมชนใหม่"])
    assert hit(sovi.check_community(t, c)) == {("S02", "S0002")}
    out = sovi.enrich(t, c)
    assert [r["community_key"] for r in out.rows] == ["ทรัพย์สินพัฒนา", "ราศรีธรรม", None]
    assert [r["community_code"] for r in out.rows] == ["71", None, None]


def test_s03_income_band_must_be_a_questionnaire_option():
    c = dict(C, allowed_values={"รายได้": ["น้อยกว่า 15,000 บาท", "100,000 บาทขึ้นไป"]})
    t = tbl(รายได้=["น้อยกว่า 15,000 บาท", "100,000 บาทขึ้นไป", "ล้านนึง"])
    assert hit(sovi.check_domain(t, c)) == {("S03", "S0002")}


def test_s04_yes_no_gate_must_agree_with_count():
    c = dict(C, gate_counts=[{"gate": "8.ผู้พิการ", "none_value": "ไม่มี", "count": "8.1"}])
    t = tbl(**{"8.ผู้พิการ": ["ไม่มี", "ไม่มี", "มี", "มี"], "8.1": [0, 1, 0, 2]})
    assert hit(sovi.check_gate_counts(t, c)) == {("S04", "S0001"), ("S04", "S0002")}


def test_s05_household_size_band_must_match_member_totals():
    c = dict(C, household_size={"column": "size", "totals": ["male", "female"],
                                "bands": {"1": [1, 1], "2–3": [2, 3], "8+": [8, 99]}})
    t = tbl(size=["1", "2-3", "8+", "1"], male=[1, 2, 5, 1], female=[0, 1, 4, 1])
    assert hit(sovi.check_household_size(t, c)) == {("S05", "S0003")}


def test_s06_scores_must_be_in_key_range_except_count_columns():
    c = dict(C, score_pattern=r"^\s*[vV]\s*_?\d", score_allowed=[0, 1, 2, 3], score_exceptions={"V50.7": [0, 10]})
    t = tbl(**{"v5.ประเภท": [1, 3, 4], "V50.7": [6, 0, 0], "5.ประเภท": ["x", "y", "z"]})
    assert hit(sovi.check_scores(t, c)) == {("S06", "S0002")}


def test_w08_member_total_differs_from_sum_of_parts_dash_counts_as_zero():
    c = dict(C, member_sums=[{"total": "ชาย", "parts": ["6.1", "6.2"]}])
    t = tbl(ชาย=[3, 3, 1], **{"6.1": [1, "-", None], "6.2": [2, 2, 1]})
    assert hit(sovi.check_warnings(t, c)) == {("W08", "S0001")}


def test_w09_rows_identical_except_id_are_warned():
    t = tbl(a=[1, 1, 2])
    assert hit(sovi.check_warnings(t, dict(C, id_columns=[ID]))) == {("W09", "S0000"), ("W09", "S0001")}
