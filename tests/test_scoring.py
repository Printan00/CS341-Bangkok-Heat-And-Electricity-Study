"""Five-group household risk score (reports/risk_score_formulas.md): the formulas on single trusted rows."""
import math

import pytest

from common import lake
from integrate import scoring

C = lake.contract("happy_home")
BANDS = [b[0] for b in C["income_bands"]]


def near(x):
    """Scores are stored with 6 decimals (R7)."""
    return pytest.approx(x, abs=1e-6)


def row(**over):
    """A trusted row for an ordinary household: the same answers as tests/hh_factory.household()."""
    base = {
        "household_code": "HH-000001", "batch_id": "happy_home-0123456789ab", "source_row": 2,
        "a6_income_stability_clean": "รายได้สม่ำเสมอ", "a7_income_band_clean": "10,001–20,000 บาท",
        "a8_expense_band_clean": "10,001–20,000 บาท", "a10_savings_clean": "มี", "a11_debt_clean": "ไม่มี",
        "a14_tenure_clean": "เป็นเจ้าของเอง", "g8_support_source_clean": "ครอบครัว/ญาติ",
        "b4_roof_material_clean": "กระเบื้อง", "b6_ceiling_clean": "มี", "b7_insulation_clean": "มี",
        "b8_ventilation_clean": "ดี", "b9_shade_clean": "มาก",
        "c2_1_heat_level_clean": "ร้อนบ่อย", "d1_1_heat_income_impact_clean": "บางส่วน",
        "d2_1_heat_health_problem_clean": "ไม่เคย", "d2_2_heat_stress_clean": "เล็กน้อย",
        "burden_min": 1001 / 20000, "burden_max": 2000 / 10001,
        "c2_5_sleep_loss": 1, "c2_5_discomfort": 0, "c2_5_headache_fatigue": 0, "c2_5_work_difficulty": 0,
        "c2_5_child_study_difficulty": 0, "c2_5_bill_increase": 0,
        "a13_elderly": 1, "a13_disabled": 0, "a13_chronic_ill": 0, "a13_bedridden": 0,
        "b12_no_budget": 0, "b12_limited_space": 1, "b12_renter_no_say": 0, "b12_dont_know_how": 0,
        "b12_costly": 0,
    }
    return {**base, **over}


# ---------- every answer of every scored question is accounted for ----------

def test_every_allowed_answer_is_scored_or_marked_not_counted():
    for code, table in scoring.ANSWER_SCORES.items():
        assert set(table) == set(C["questions"][code]["allowed"]), code  # a typo would silently drop an item
        assert all(v is None or 0 <= v <= 1 for v in table.values()), code


def test_unsure_answers_are_not_counted():
    for code in ("B6", "B7", "B8"):
        assert scoring.ANSWER_SCORES[code]["ไม่แน่ใจ"] is None


# ---------- one group at a time ----------

def test_ordinary_household_heat_risk():
    # C2.1 ร้อนบ่อย 2/3, 1 of 5 symptoms, D1.1 บางส่วน 1/2, D2.1 0, D2.2 0, A13 elderly 1
    assert scoring.heat_risk(row()) == near((2 / 3 + 1 / 5 + 1 / 2 + 0 + 0 + 1) / 6)


def test_heat_counts_an_unsure_income_impact_as_zero_but_not_a_missing_core_item():
    assert scoring.heat_risk(row(d1_1_heat_income_impact_clean=None)) == near((2 / 3 + 1 / 5 + 0 + 1) / 6)
    assert scoring.heat_risk(row(c2_1_heat_level_clean=None)) is None


def test_heat_allows_one_other_item_to_be_missing_but_not_two():
    one = scoring.heat_risk(row(d2_1_heat_health_problem_clean=None))
    assert one == near((2 / 3 + 1 / 5 + 1 / 2 + 0 + 1) / 5)
    assert scoring.heat_risk(row(d2_1_heat_health_problem_clean=None, d2_2_heat_stress_clean=None)) is None


def test_housing_risk_steps_ventilation_and_shade():
    worst = row(b4_roof_material_clean="สังกะสี/เมทัลชีท", b6_ceiling_clean="ไม่มี", b7_insulation_clean="ไม่มี",
                b8_ventilation_clean="ไม่ดี", b9_shade_clean="ไม่มีเลย")
    assert scoring.housing_risk(worst) == 1.0
    assert scoring.housing_risk(row()) == 0.0
    assert scoring.housing_risk(row(b8_ventilation_clean="ปานกลาง", b9_shade_clean="น้อย")) == \
        near((0.5 + 2 / 3) / 5)


def test_housing_needs_four_of_five_items():
    assert scoring.housing_risk(row(b6_ceiling_clean=None, b8_ventilation_clean="ไม่ดี")) == near(1 / 4)
    assert scoring.housing_risk(row(b6_ceiling_clean=None, b7_insulation_clean=None)) is None


def test_finance_risk_uses_stability_debt_savings_and_expense_above_income():
    worst = row(a6_income_stability_clean="รายได้ไม่แน่นอน", a11_debt_clean="มากกว่า 50,000 บาท",
                a10_savings_clean="ไม่มี", a8_expense_band_clean="20,001–50,000 บาท")
    assert scoring.finance_risk(worst, BANDS) == 1.0
    assert scoring.finance_risk(row(), BANDS) == 0.0
    mid = row(a6_income_stability_clean="รายได้ตามฤดูกาล", a11_debt_clean="5,000–10,000 บาท")
    assert scoring.finance_risk(mid, BANDS) == near((0.5 + 0.5 + 0 + 0) / 4)


def test_finance_expense_equal_to_or_below_income_is_not_a_risk():
    below = row(a7_income_band_clean="20,001–50,000 บาท", a8_expense_band_clean="10,001–20,000 บาท")
    assert scoring.finance_risk(below, BANDS) == 0.0


def test_finance_needs_three_of_four_items():
    assert scoring.finance_risk(row(a6_income_stability_clean=None, a11_debt_clean="น้อยกว่า 5,000 บาท"), BANDS) \
        == near(0.25 / 3)
    assert scoring.finance_risk(row(a6_income_stability_clean=None, a11_debt_clean=None), BANDS) is None
    assert scoring.finance_risk(row(a8_expense_band_clean=None, a10_savings_clean=None), BANDS) is None


@pytest.mark.parametrize("bmin, bmax, expected", [
    (0.10, 0.40, 1.0),                      # spec example 1: geometric middle 20% = the cap
    (0.01, 0.05, math.sqrt(0.01 * 0.05) / 0.20),  # spec example 2: about 0.11
    (0.0, 0.30, 0.15 / 0.20),               # bill band 'under 500' has min 0: half of b_max
    (0.30, 0.50, 1.0),                      # above the cap stays at 1
    (0.0, 0.0, 0.0),
])
def test_burden_risk(bmin, bmax, expected):
    assert scoring.burden_risk(row(burden_min=bmin, burden_max=bmax)) == near(expected)


def test_burden_risk_is_null_without_a_burden_range():
    assert scoring.burden_risk(row(burden_min=None, burden_max=None)) is None


def test_coping_risk_counts_tenure_barriers_and_support():
    worst = row(a14_tenure_clean="เช่า", g8_support_source_clean="ไม่มี", b12_no_budget=1, b12_costly=1)
    assert scoring.coping_risk(worst) == 1.0
    assert scoring.coping_risk(row()) == near(0.5 / 3)  # one barrier = ½
    assert scoring.coping_risk(row(b12_limited_space=0)) == 0.0


def test_coping_needs_two_of_three_items():
    assert scoring.coping_risk(row(g8_support_source_clean=None)) == near(0.5 / 2)
    assert scoring.coping_risk(row(g8_support_source_clean=None, a14_tenure_clean=None)) is None


# ---------- all five together ----------

def test_total_is_100_times_the_mean_of_five_groups():
    groups = {"heat_risk": 0.5, "housing_risk": 0.6, "finance_risk": 0.4, "burden_risk": 0.7, "coping_risk": 0.2}
    out = scoring.combine(groups)
    assert out["risk_score"] == near(48.0)
    assert out["exposure"] == near(0.55)
    assert out["vulnerability"] == near((0.4 + 0.7 + 0.2) / 3)


def test_total_is_null_when_any_group_is_null():
    groups = {"heat_risk": 0.5, "housing_risk": None, "finance_risk": 0.4, "burden_risk": 0.7, "coping_risk": 0.2}
    out = scoring.combine(groups)
    assert out["risk_score"] is None and out["risk_quadrant"] is None
    assert out["exposure"] is None and out["vulnerability"] == near((0.4 + 0.7 + 0.2) / 3)


@pytest.mark.parametrize("exposure, vulnerability, quadrant", [
    (0.8, 0.8, "help_first"), (0.8, 0.2, "watch"), (0.2, 0.8, "low_heat_limited"), (0.2, 0.2, "low_heat_coping"),
])
def test_quadrants(exposure, vulnerability, quadrant):
    assert scoring.quadrant(exposure, vulnerability) == quadrant


def test_a_value_of_exactly_0_5_is_the_high_side():
    """Real data has households exactly on the cut; counting 0.5 as high reproduces the spec's 26/35/8/19."""
    assert scoring.quadrant(0.5, 0.5) == "help_first"
    assert scoring.quadrant(0.5, 0.4999) == "watch" and scoring.quadrant(0.4999, 0.5) == "low_heat_limited"


def test_ranks_share_ties():
    assert scoring.ranks([0.5, 2.0, None, 2.0, 1.0]) == [4, 1, None, 1, 3]


def test_risk_rows_follow_the_contract_and_rank_the_riskiest_first():
    risky = row(household_code="HH-000002", c2_1_heat_level_clean="ร้อนมากทุกวัน", g8_support_source_clean="ไม่มี")
    rows = scoring.risk_rows([row(), risky], C["income_bands"], lake.contract("curated_happy_home_risk"))
    assert [r["household_code"] for r in rows] == ["HH-000001", "HH-000002"]
    assert [r["risk_rank"] for r in rows] == [2, 1]
    assert set(rows[0]) == {c["name"] for c in lake.contract("curated_happy_home_risk")["columns"]}
    assert rows[0]["batch_id"] == "happy_home-0123456789ab" and rows[0]["source_row"] == 2


def test_score_is_not_gated_on_usable_q3():
    """Unlike the old T13 score: every group has its own missing-item rule, and the real file has no gated row."""
    rows = scoring.risk_rows([row(usable_q3=False)], C["income_bands"], lake.contract("curated_happy_home_risk"))
    assert rows[0]["risk_score"] is not None
