"""Five-group household risk score (reports/risk_score_formulas.md, D8-D20) on trusted rows.

Every score is 0-1 and higher means riskier. Item scores come from fixed tables (R2), never from the
data's own spread. Answers the questionnaire marks "not sure" are not counted (None in the tables).

Missing items: housing needs 4 of 5, finance 3 of 4, coping 2 of 3 (R5, D16).
Heat is not covered by R5. Rule used here (D18, same idea as D16): C2.1 and C2.5 are required
(the core items of T10) and at most one of the other four may be missing; D1.1 "unsure" counts 0 (T10).

LST (D21/D25, reports/gee_lst_pipeline.md): land surface temperature is joined as separate columns, on the
fixed 30-45 deg C range -> 0-1. It is NOT in risk_score.
  community level (community_dim, on community_key): lst_mean_c, lst_score, lst_batch_id
  household level (household_lst, on household_code): lst_hh_c, lst_hh_score, lst_hh_batch_id
"""
import math

BURDEN_CAP = 0.20      # D12: burden at or above 20% of income scores 1
CUT = 0.5              # D13: both axes are cut at 0.5
DIGITS = 6             # R7

# questionnaire answer -> 0-1 score; None = allowed answer that is not counted
ANSWER_SCORES = {
    "A6": {"รายได้สม่ำเสมอ": 0, "รายได้ตามฤดูกาล": 0.5, "รายได้ไม่แน่นอน": 1, "รายได้ขึ้นอยู่กับสภาพอากาศ/ภัยพิบัติ": 1},
    "A10": {"มี": 0, "ไม่มี": 1},
    "A11": {"ไม่มี": 0, "น้อยกว่า 5,000 บาท": 0.25, "5,000–10,000 บาท": 0.5, "10,001–50,000 บาท": 0.75,
            "มากกว่า 50,000 บาท": 1},
    "A14": {"เป็นเจ้าของเอง": 0, "เช่า": 1, "อยู่กับญาติ": 1, "อยู่อาศัยแบบไม่เป็นทางการ": 1, "อื่น ๆ": 1},
    "G8": {"ครอบครัว/ญาติ": 0, "เพื่อนบ้าน": 0, "ผู้นำชุมชน": 0, "หน่วยงานรัฐ": 0, "ไม่มี": 1, "อื่น ๆ": 0},
    "B4": {"กระเบื้อง": 0, "สังกะสี/เมทัลชีท": 1, "คอนกรีต": 0, "อื่น ๆ": 0},
    "B6": {"มี": 0, "ไม่มี": 1, "ไม่แน่ใจ": None},
    "B7": {"มี": 0, "ไม่มี": 1, "ไม่แน่ใจ": None},
    "B8": {"ดี": 0, "ปานกลาง": 0.5, "ไม่ดี": 1, "ไม่แน่ใจ": None},
    "B9": {"มาก": 0, "พอมี": 1 / 3, "น้อย": 2 / 3, "ไม่มีเลย": 1},
    "C2.1": {"ร้อนมากทุกวัน": 1, "ร้อนบ่อย": 2 / 3, "ร้อนบางวัน": 1 / 3, "ไม่ค่อยร้อน": 0},
    "D1.1H": {"มาก": 1, "บางส่วน": 0.5, "ไม่กระทบ": 0, "ไม่แน่ใจ": 0},  # T10: unsure counts 0
    "D2.1H": {"เคย": 1, "ไม่เคย": 0},
    "D2.2H": {"มาก": 1, "ปานกลาง": 0.5, "เล็กน้อย": 0, "ไม่เลย": 0},
}
COLUMN = {
    "A6": "a6_income_stability_clean", "A10": "a10_savings_clean", "A11": "a11_debt_clean",
    "A14": "a14_tenure_clean", "G8": "g8_support_source_clean",
    "B4": "b4_roof_material_clean", "B6": "b6_ceiling_clean", "B7": "b7_insulation_clean",
    "B8": "b8_ventilation_clean", "B9": "b9_shade_clean",
    "C2.1": "c2_1_heat_level_clean", "D1.1H": "d1_1_heat_income_impact_clean",
    "D2.1H": "d2_1_heat_health_problem_clean", "D2.2H": "d2_2_heat_stress_clean",
}
SYMPTOMS = ["c2_5_sleep_loss", "c2_5_discomfort", "c2_5_headache_fatigue", "c2_5_work_difficulty",
            "c2_5_child_study_difficulty"]  # "bill increase" is not a heat symptom
VULNERABLE = ["a13_elderly", "a13_disabled", "a13_chronic_ill", "a13_bedridden"]  # D10: 4 groups
BARRIERS = ["b12_no_budget", "b12_limited_space", "b12_renter_no_say", "b12_dont_know_how", "b12_costly"]
GROUPS = ["heat_risk", "housing_risk", "finance_risk", "burden_risk", "coping_risk"]


def item(row, code):
    """Score of one single-answer item; None when blank, unsure or not an allowed answer."""
    return ANSWER_SCORES[code].get(row.get(COLUMN[code]))


def mean(scores, minimum):
    """Mean of the answered (not None) scores, None when fewer than `minimum` are answered."""
    got = [s for s in scores if s is not None]
    return round(sum(got) / len(got), DIGITS) if len(got) >= minimum and got else None


def flags(row, names):
    """Multi-select 0/1 columns -> the number ticked, None when none of the columns has an answer."""
    values = [row.get(n) for n in names]
    return None if all(v is None for v in values) else sum(v == 1 for v in values)


def heat_risk(row):
    level = item(row, "C2.1")
    symptoms = flags(row, SYMPTOMS)
    if level is None or symptoms is None:
        return None
    members = flags(row, VULNERABLE)
    scores = [level, symptoms / len(SYMPTOMS), item(row, "D1.1H") or 0, item(row, "D2.1H"), item(row, "D2.2H"),
              None if members is None else float(members > 0)]
    return mean(scores, 5)


def housing_risk(row):
    return mean([item(row, c) for c in ("B4", "B6", "B7", "B8", "B9")], 4)


def expense_above_income(row, income_bands):
    income, expense = row.get("a7_income_band_clean"), row.get("a8_expense_band_clean")
    if income not in income_bands or expense not in income_bands:
        return None
    return float(income_bands.index(expense) > income_bands.index(income))


def finance_risk(row, income_bands):
    return mean([item(row, "A6"), item(row, "A11"), item(row, "A10"), expense_above_income(row, income_bands)], 3)


def burden_risk(row):
    lo, hi = row.get("burden_min"), row.get("burden_max")
    if lo is None or hi is None:
        return None
    middle = math.sqrt(lo * hi) if lo > 0 else hi / 2  # D12: geometric middle; half of b_max when b_min is 0
    return round(min(middle / BURDEN_CAP, 1.0), DIGITS)


def coping_risk(row):
    barriers = flags(row, BARRIERS)
    barrier = None if barriers is None else (0 if barriers == 0 else 0.5 if barriers == 1 else 1)
    return mean([item(row, "A14"), barrier, item(row, "G8")], 2)


def quadrant(exposure, vulnerability):
    """D13: cut at 0.5 on both axes; a value of exactly 0.5 counts as the high side."""
    if exposure is None or vulnerability is None:
        return None
    hot, limited = exposure >= CUT, vulnerability >= CUT
    return {(True, True): "help_first", (True, False): "watch",
            (False, True): "low_heat_limited", (False, False): "low_heat_coping"}[(hot, limited)]


def combine(groups):
    """groups: the five group scores -> exposure, vulnerability, risk_score (0-100) and quadrant."""
    exposure = mean([groups["heat_risk"], groups["housing_risk"]], 2)
    vulnerability = mean([groups["finance_risk"], groups["burden_risk"], groups["coping_risk"]], 3)
    values = [groups[g] for g in GROUPS]
    score = None if any(v is None for v in values) else round(100 * sum(values) / len(values), DIGITS)  # R6
    return {"exposure": exposure, "vulnerability": vulnerability, "risk_score": score,
            "risk_quadrant": quadrant(exposure, vulnerability)}


def ranks(scores):
    """1 = highest score; equal scores share a rank (1, 2, 2, 4). None stays None."""
    ordered = sorted((s for s in scores if s is not None), reverse=True)
    first = {}
    for i, s in enumerate(ordered, start=1):
        first.setdefault(s, i)
    return [first[s] if s is not None else None for s in scores]


def lst_score(lst_c, score_range):
    """D21: LST (deg C) on a fixed range -> 0-1; at or below the low end 0, at or above the high end 1 (R2)."""
    if lst_c is None:
        return None
    lo, hi = score_range
    return round(min(max((lst_c - lo) / (hi - lo), 0.0), 1.0), DIGITS)


COMMUNITY_LST = ("lst_mean_c", "lst_score", "lst_batch_id")
HOUSEHOLD_LST = ("lst_hh_c", "lst_hh_score", "lst_hh_batch_id")


def lst_fields(source_row, columns=COMMUNITY_LST):
    """source_row: the published community_dim / household_lst row for this household, or None (no LST)."""
    if source_row is None:
        return dict.fromkeys(columns)
    return dict(zip(columns, (source_row["lst_mean_c"], source_row["lst_score"], source_row["batch_id"])))


def risk_rows(trusted, income_bands, schema, lst=None, lst_hh=None):
    """One record per trusted row with exactly the columns of contracts/curated_happy_home_risk.json.

    lst: community_key -> published community_dim row; lst_hh: household_code -> published household_lst row
    (empty or None: those LST columns are null).
    """
    names = [c["name"] for c in schema["columns"]]
    lst, lst_hh = lst or {}, lst_hh or {}
    out = []
    for t in trusted:
        groups = {"heat_risk": heat_risk(t), "housing_risk": housing_risk(t),
                  "finance_risk": finance_risk(t, income_bands), "burden_risk": burden_risk(t),
                  "coping_risk": coping_risk(t)}
        row = {**t, **groups, **combine(groups), **lst_fields(lst.get(t.get("community_key"))),
               **lst_fields(lst_hh.get(t.get("household_code")), HOUSEHOLD_LST)}
        out.append({n: row.get(n) for n in names})
    for row, r in zip(out, ranks([r["risk_score"] for r in out])):
        row["risk_rank"] = r
    return out
