"""gee_lst_household source (one LST row per household, D25): Validate -> Transform -> Integrate -> Verify ->
household_lst, and the Happy Home join on household_code into happy_home_risk (lst_hh_*)."""
import json

import pytest

from check_batch.handler import handler as check_batch
from common import lake, parquet
from hh_factory import household, town, workbook
from integrate.handler import handler as integrate
from transform.handler import handler as transform
from validate.handler import handler as validate
from verify.handler import VerifyFailed, handler as verify

GHH = "gee_lst_household-0123456789ab"
HH = "happy_home-0123456789ab"
Q = "quarantine/gee_lst_household/%s/" % GHH
HEADER = ["household_code", "lst_mean_c", "n_scenes", "period", "buffer_m", "source"]
TAIL = ["22", "2026-03-01..2026-05-31", "50", "landsat8/9_c02_l2_ST_B10"]


def hh_rows(temps):
    """{household number: LST} -> CSV rows keyed like hh_factory (HH-000001 ...)."""
    return [["HH-%06d" % i, str(t)] + TAIL for i, t in temps.items()]


def csv_bytes(rows, header=HEADER):
    return ("\n".join([",".join(header)] + [",".join(r) for r in rows]) + "\n").encode("utf-8")


def run_ghh(s3, rows, header=HEADER):
    s3.objects["raw/gee_lst_household/%s/gee_lst_household.csv" % GHH] = csv_bytes(rows, header)
    ev = {"batch_id": GHH}
    for step in (validate, transform, integrate, verify):
        ev = step(ev, None)
    return ev


def run_hh(s3, rows):
    s3.objects["raw/happy_home/%s/survey.xlsx" % HH] = workbook(rows)
    ev = {"batch_id": HH, "force": True}
    for step in (check_batch, validate, transform, integrate, verify):
        ev = step(ev, None)
    return ev


def table(s3, key):
    return parquet.read(s3.objects[key]).to_pylist()


def test_household_batch_publishes_household_lst(s3):
    out = run_ghh(s3, hh_rows({1: 43.4, 2: 41.7, 3: 42.9}))
    assert out["verified"] is True
    rows = table(s3, lake.curated_key("household_lst"))
    assert list(rows[0]) == [c["name"] for c in lake.contract("curated_household_lst")["columns"]]
    got = {r["household_code"]: (r["lst_mean_c"], r["lst_score"], r["buffer_m"]) for r in rows}
    assert got["HH-000001"] == (43.4, pytest.approx(13.4 / 15), 50.0)
    marker = json.loads(s3.objects[lake.success_key(GHH)])
    assert marker["table"] == "household_lst" and marker["household_lst_rows"] == 3


def test_household_report_masks_small_counts_and_quarantines_bad_rows(s3):
    rows = hh_rows({1: 43.4, 2: 41.7}) + [["", "40.0"] + TAIL, ["HH-000001", "42.0"] + TAIL]
    s3.objects["raw/gee_lst_household/%s/gee_lst_household.csv" % GHH] = csv_bytes(rows)
    out = validate({"batch_id": GHH}, None)
    assert (out["rows_passed"], out["rows_quarantined"]) == (1, 3)  # blank code (G04) + both HH-000001 (G05)
    rep = json.loads(s3.objects[Q + "dq_report.json"])
    assert rep["rules"] == {"G04": {"FAIL": "<5"}, "G05": {"FAIL": "<5"}}
    man = json.loads(s3.objects[Q + "manifest.json"])
    assert [p["household_code"] for p in man["passed"]] == ["HH-000002"]


@pytest.mark.parametrize("extra", ["lat", "community"])
def test_household_file_with_coordinates_or_community_is_refused(s3, extra):
    rows = [r + ["x"] for r in hh_rows({1: 43.4})]
    s3.objects["raw/gee_lst_household/%s/gee_lst_household.csv" % GHH] = csv_bytes(rows, HEADER + [extra])
    assert validate({"batch_id": GHH}, None)["valid"] is False
    assert json.loads(s3.objects[Q + "dq_report.json"])["batch_errors"][0].startswith("G03")
    assert s3.objects[Q + "rows.jsonl"] == b""


def test_each_household_gets_its_own_lst_and_missing_ones_get_null(s3):
    run_ghh(s3, hh_rows({1: 43.4, 2: 41.7, 99: 44.0, 500: 40.0}))  # 500 is not in the survey: ignored
    run_hh(s3, town(4) + [household(99, community="F")])
    risk = {r["household_code"]: r for r in table(s3, lake.curated_key("happy_home_risk"))}
    assert (risk["HH-000001"]["lst_hh_c"], risk["HH-000001"]["lst_hh_batch_id"]) == (43.4, GHH)
    assert risk["HH-000002"]["lst_hh_score"] == pytest.approx(11.7 / 15)
    assert risk["HH-000099"]["lst_hh_c"] == 44.0  # unknown community, but its own point has a value
    assert risk["HH-000003"]["lst_hh_c"] is None and risk["HH-000003"]["lst_mean_c"] is None
    marker = json.loads(s3.objects[lake.success_key(HH)])
    assert marker["lst_hh_batch_ids"] == [GHH] and marker["lst_hh_households"] == 3


def test_household_lst_is_the_sixth_part_of_risk_score(s3):
    """D27: risk_score = 100 x mean(five survey groups + lst_hh_score); D28: no LST -> mean of the five."""
    run_ghh(s3, hh_rows({1: 45.0, 2: 30.0, 3: 37.5}))  # scores 1.0, 0.0, 0.5; household 4 has no LST
    run_hh(s3, town(4))
    groups = ["heat_risk", "housing_risk", "finance_risk", "burden_risk", "coping_risk"]
    for r in table(s3, lake.curated_key("happy_home_risk")):
        survey = [r[g] for g in groups]
        if r["household_code"] == "HH-000004":
            assert r["lst_hh_score"] is None
            assert r["risk_score"] == pytest.approx(100 * sum(survey) / 5, abs=1e-4)
            assert r["exposure"] == pytest.approx((r["heat_risk"] + r["housing_risk"]) / 2, abs=1e-6)
        else:
            assert r["risk_score"] == pytest.approx(100 * (sum(survey) + r["lst_hh_score"]) / 6, abs=1e-4)
            assert r["exposure"] == pytest.approx((r["heat_risk"] + r["housing_risk"] + r["lst_hh_score"]) / 3,
                                                  abs=1e-6)


def test_community_lst_stays_out_of_risk_score(s3):
    from test_gee import run_gee
    run_hh(s3, town(4))
    before = {r["household_code"]: r["risk_score"] for r in table(s3, lake.curated_key("happy_home_risk"))}
    run_gee(s3)
    run_hh(s3, town(4))
    after = table(s3, lake.curated_key("happy_home_risk"))
    assert {r["household_code"]: r["risk_score"] for r in after} == before
    assert all(r["lst_mean_c"] is not None for r in after)


@pytest.mark.parametrize("change", [
    lambda r: r.update(lst_hh_c=50.0, lst_hh_score=1.0),   # not the household's published value
    lambda r: r.update(lst_hh_score=0.1),                  # not the fixed scale
    lambda r: r.update(lst_hh_batch_id=None),
])
def test_verify_refuses_a_wrong_household_join(s3, change):
    run_ghh(s3, hh_rows({1: 43.4, 2: 41.7, 3: 42.9, 4: 42.0}))
    s3.objects["raw/happy_home/%s/survey.xlsx" % HH] = workbook(town(4))
    ev = {"batch_id": HH}
    for step in (validate, transform, integrate):
        ev = step(ev, None)
    key = lake.staging_key(HH, "happy_home_risk")
    rows = table(s3, key)
    change(rows[0])
    s3.objects[key] = parquet.to_bytes(rows, lake.contract("curated_happy_home_risk"))
    with pytest.raises(VerifyFailed, match="household_lst|lst_hh_score"):
        verify(ev, None)
    assert lake.curated_key("happy_home_risk") not in s3.objects
