"""The spec's "ผลกับข้อมูลจริง" numbers on the real Happy Home file (88 rows).

Runs only with BHES_SAMPLE_DIR set (the survey file is never committed). Only totals are
asserted here, no household ids or coordinates.
"""
import hashlib
import math
import random
import statistics
from collections import Counter

import pytest

from common import lake, parquet
from common.xlsx import read_workbook
from integrate import scoring
from integrate.handler import handler as integrate
from transform.handler import handler as transform
from validate.handler import handler as validate
from stats_helper import dirichlet_ones, permutation_p, spearman
from validate.rules import required_columns
from verify.handler import handler as verify


@pytest.fixture
def run(s3, real_hh_bytes):
    batch = "happy_home-" + hashlib.sha256(real_hh_bytes).hexdigest()[:12]
    s3.objects["raw/happy_home/%s/survey.xlsx" % batch] = real_hh_bytes
    ev = {"batch_id": batch}
    for step in (validate, transform, integrate, verify):
        ev = step(ev, None)
    trusted = parquet.read(s3.objects[lake.trusted_key(batch)]).to_pylist()
    curated = parquet.read(s3.objects[lake.curated_key("happy_home_household")]).to_pylist()
    manifest = lake.get_json(lake.quarantine_prefix(batch) + "manifest.json")
    return ev, trusted, curated, manifest


def test_every_contract_column_is_in_the_real_header(real_hh_bytes, contract):
    header = read_workbook(real_hh_bytes)[contract["data_sheet"]].header
    assert [c for c in required_columns(contract) if c not in header] == []


def test_validate_numbers(run):
    ev, _, _, manifest = run
    assert (ev["rows_passed"], ev["rows_quarantined"]) == (88, 0)  # only V01/V02 blank/V05 quarantine
    flags = Counter(f for p in manifest["passed"] for f in p["dq_flags"])
    assert flags["V10"] == 7  # D3: lowest income band + summer bill over 3,000
    assert flags["V04"] < 5  # outside Bangkok or without coordinates
    assert flags["V08"] == flags["V09"] == flags["V13"] == 0
    stopped_before_b = sum(1 for p in manifest["passed"] if not (p["usable_q1"] or p["usable_q2"] or p["usable_q3"]))
    assert stopped_before_b == 0  # D4
    unknown = [p for p in manifest["passed"] if p["community_key"] == "unknown"]
    assert len(unknown) == 7 and 0 < sum(1 for p in unknown if p["community_suggested"]) < 5  # D5


def test_transform_numbers(run):
    _, trusted, _, _ = run
    assert Counter(r["burden_class"] for r in trusted) == {"high": 35, "possibly_high": 31, "low": 22}  # D2 10%
    assert Counter(r["burden_class_6pct"] for r in trusted) == {"high": 37, "possibly_high": 46, "low": 5}
    capped = [r for r in trusted if r["income_ord"] == 5 and r["bill_summer_ord"] == 5]
    assert all(r["burden_class"] == "possibly_high" for r in capped) and 0 < len(capped) < 5  # D1 cap
    assert Counter(r["heat_impact_level"] for r in trusted) == {"low": 15, "medium": 45, "high": 28}  # D6
    assert sum(r["coping_limited"] for r in trusted) == 30  # D6
    assert min(r["housing_items_answered"] for r in trusted) >= 4  # T09
    assert Counter(r["c2_8_heat_retrofit_clean"] for r in trusted) == {"เคย": 11, "ไม่เคย": 77}


def test_risk_top_20_is_the_same_under_both_weightings(run):
    _, _, curated, _ = run
    top = {col: {r["household_code"] for r in curated if r[col] is not None and r[col] <= 20}
           for col in ("risk_rank", "risk_rank_equal")}
    assert top["risk_rank"] == top["risk_rank_equal"]  # D7 (a tie at rank 20 makes the group 21)


def test_verify_marker(run):
    ev, trusted, curated, _ = run
    assert ev["verified"] is True and len(trusted) == len(curated) == 88


# ---------- five-group risk score: the numbers published in reports/risk_score_formulas.md (section 4-5) ----------

@pytest.fixture
def risk(s3, run):
    ev, *_ = run
    return parquet.read(s3.objects[lake.curated_key("happy_home_risk")]).to_pylist()


def test_risk_table_has_a_complete_score_for_every_household(risk):
    assert len(risk) == 88 and all(r["risk_score"] is not None for r in risk)


def test_risk_distribution_matches_the_spec(risk):
    # Section 5.1 reads the median as sorted[n // 2], the upper of the two middle values when n = 88
    # (heat 0.56 and risk_score 49.7; the average of the two middles would be 0.55 and 49.1).
    expected = {  # group: (min, median, max, mean) from section 5.1
        "heat_risk": (0.12, 0.56, 0.90, 0.54), "housing_risk": (0.00, 0.60, 1.00, 0.58),
        "finance_risk": (0.00, 0.38, 1.00, 0.39), "burden_risk": (0.05, 0.50, 1.00, 0.60),
        "coping_risk": (0.00, 0.17, 1.00, 0.31), "exposure": (0.18, 0.59, 0.87, 0.56),
        "vulnerability": (0.06, 0.46, 0.94, 0.43), "risk_score": (17.6, 49.7, 81.0, 48.2),
    }
    for col, want in expected.items():
        values = [r[col] for r in risk]
        got = (min(values), statistics.median_high(values), max(values), statistics.fmean(values))
        assert tuple(round(v, 2 if col != "risk_score" else 1) for v in got) == want, col


def test_burden_risk_buckets_and_the_cap(risk):
    values = [r["burden_risk"] for r in risk]
    buckets = (sum(v < 0.25 for v in values), sum(0.25 <= v < 0.5 for v in values),
               sum(0.5 <= v < 0.75 for v in values), sum(0.75 <= v < 1 for v in values), sum(v == 1 for v in values))
    assert buckets == (22, 20, 11, 5, 30)


def test_quadrants_at_0_5(risk):
    assert Counter(r["risk_quadrant"] for r in risk) == \
        {"help_first": 26, "watch": 35, "low_heat_limited": 8, "low_heat_coping": 19}


def test_expense_above_income_count(run):
    _, trusted, _, _ = run
    bands = [b[0] for b in lake.contract("happy_home")["income_bands"]]
    assert sum(scoring.expense_above_income(t, bands) == 1 for t in trusted) == 19


def test_every_scored_answer_in_the_real_file_is_in_the_tables(run):
    """A spelling the tables do not know would silently drop the item, so none may appear."""
    _, trusted, _, _ = run
    for code, table in scoring.ANSWER_SCORES.items():
        seen = {t[scoring.COLUMN[code]] for t in trusted} - {None}
        assert seen <= set(table), (code, seen - set(table))


# ---------- sections 5.2-5.4: correlations, weight test and the E2.6 check ----------

GROUPS = ["heat_risk", "housing_risk", "finance_risk", "burden_risk", "coping_risk"]


def test_group_correlations_match_the_spec(risk):
    want = {("heat_risk", "housing_risk"): 0.12, ("heat_risk", "finance_risk"): 0.00,
            ("heat_risk", "burden_risk"): 0.05, ("heat_risk", "coping_risk"): -0.03,
            ("housing_risk", "finance_risk"): 0.22, ("housing_risk", "burden_risk"): 0.21,
            ("housing_risk", "coping_risk"): 0.01, ("finance_risk", "burden_risk"): 0.53,
            ("finance_risk", "coping_risk"): 0.28, ("burden_risk", "coping_risk"): 0.09}
    got = {pair: round(spearman([r[pair[0]] for r in risk], [r[pair[1]] for r in risk]), 2) for pair in want}
    assert got == want
    assert max(abs(v) for v in got.values()) == 0.53  # finance-burden, the largest after income was dropped


def top_group(scores, k):
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    return set(order[:k])


def test_top_group_is_fairly_stable_under_random_weights(risk):
    """5.3: 5,000 Dirichlet(1,1,1,1,1) weightings; the spec reports about 72% overlap with the equal-weight top 18.

    The spec's script and its seed are gone, so this checks a band around the published numbers, not the numbers.
    """
    rng = random.Random(20260718)
    scores = [[r[g] for g in GROUPS] for r in risk]
    equal = top_group([sum(row) for row in scores], 18)
    overlaps, times_in = [], [0] * len(risk)
    for _ in range(5000):
        w = dirichlet_ones(5, rng)
        top = top_group([sum(a * b for a, b in zip(w, row)) for row in scores], 18)
        overlaps.append(len(top & equal) / 18)
        for i in top:
            times_in[i] += 1
    assert 0.68 <= statistics.fmean(overlaps) <= 0.76
    assert 0.44 <= sorted(overlaps)[len(overlaps) // 20] <= 0.56  # the 5th percentile, spec 50%
    share = [t / 5000 for t in times_in]
    assert sum(share[i] >= 0.5 for i in equal) in (14, 15, 16)  # spec: 15 of the 18
    assert sum(share[i] >= 0.8 for i in equal) in (5, 6, 7)  # spec: 6 of the 18
    assert not any(share[i] > 0.5 for i in range(len(risk)) if i not in equal)  # nobody outside moves in


def test_score_tracks_having_cut_back_electricity_use_e2_6(risk, run):
    """5.4: E2.6 is not in the formula; households that cut use for the bill score higher, with or without burden."""
    _, trusted, _, _ = run
    cut = {t["household_code"]: t["e2_6_cut_use_clean"] for t in trusted}
    yes = [r for r in risk if cut[r["household_code"]] == "เคย"]
    no = [r for r in risk if cut[r["household_code"]] == "ไม่เคย"]
    assert (len(yes), len(no)) == (38, 50)
    mean = statistics.fmean
    assert (round(mean(r["risk_score"] for r in yes), 1), round(mean(r["risk_score"] for r in no), 1)) == (53.3, 44.4)

    def without_burden(r):
        return 100 * mean(r[g] for g in GROUPS if g != "burden_risk")

    assert (round(mean(map(without_burden, yes)), 1), round(mean(map(without_burden, no)), 1)) == (49.3, 42.3)
    assert permutation_p([r["risk_score"] for r in yes], [r["risk_score"] for r in no]) < 0.01  # spec p = 0.003
    assert permutation_p(list(map(without_burden, yes)), list(map(without_burden, no))) < 0.03  # spec p = 0.011


# ---------- measured effect of the design choices D10, D12 and D17 (reports/risk_score_formulas.md) ----------

def test_d7_weights_would_keep_the_same_top_18_as_equal_weights(risk):
    equal = [sum(r[g] for g in GROUPS) for r in risk]
    d7 = [sum(r[g] for g in GROUPS) + r["burden_risk"] for r in risk]  # burden counted twice
    assert top_group(equal, 18) == top_group(d7, 18)
    assert round(spearman(equal, d7), 2) == 0.97


def test_arithmetic_middle_of_the_burden_range_would_barely_change_the_top_group(risk, run):
    _, trusted, _, _ = run
    by = {t["household_code"]: t for t in trusted}
    cap = 0.20
    arithmetic = [min((by[r["household_code"]]["burden_min"] + by[r["household_code"]]["burden_max"]) / 2 / cap, 1.0)
                  for r in risk]
    current = [sum(r[g] for g in GROUPS) for r in risk]
    alternative = [sum(r[g] for g in GROUPS if g != "burden_risk") + b for r, b in zip(risk, arithmetic)]
    assert len(top_group(current, 18) & top_group(alternative, 18)) == 17
    assert round(spearman(current, alternative), 2) == 0.99


def test_counting_young_children_and_pregnancy_would_flag_few_more_households(risk, run):
    _, trusted, _, _ = run
    four = ["a13_elderly", "a13_disabled", "a13_chronic_ill", "a13_bedridden"]
    six = four + ["a13_child_under5", "a13_pregnant"]
    flagged = lambda cols: sum(any(t[c] == 1 for c in cols) for t in trusted)
    assert (flagged(four), flagged(six)) == (59, 65)
    by = {t["household_code"]: t for t in trusted}
    shift = [(any(by[r["household_code"]][c] == 1 for c in six) - any(by[r["household_code"]][c] == 1 for c in four)) / 6
             for r in risk]  # A13 is one of the six items of heat_risk, and every household answered all six
    current = [sum(r[g] for g in GROUPS) for r in risk]
    alternative = [c + d for c, d in zip(current, shift)]
    assert len(top_group(current, 18) & top_group(alternative, 18)) == 17


def test_risk_table_q2_columns_match_the_q2_results(risk):
    groups = ["1) ไม่เกิน 10,000", "2) 10,001-20,000", "3) มากกว่า 20,000"]
    assert [sum(r.get("income_group") == g for r in risk) for g in groups] == [34, 23, 31]
    assert [sum(r.get("income_group") == g and r.get("burden_class") == "high" for r in risk)
            for g in groups] == [27, 8, 0]
    assert Counter(r.get("burden_class") for r in risk) == {"high": 35, "possibly_high": 31, "low": 22}
    assert Counter(r.get("has_aircon") for r in risk) == {True: 46, False: 42}
