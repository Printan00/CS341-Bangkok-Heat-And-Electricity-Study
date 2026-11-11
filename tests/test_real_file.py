"""The spec's "ผลกับข้อมูลจริง" numbers on the real Happy Home file (88 rows).

Runs only with BHES_SAMPLE_DIR set (the survey file is never committed). Only totals are
asserted here, no household ids or coordinates.
"""
import hashlib
from collections import Counter

import pytest

from common import lake, parquet
from common.xlsx import read_workbook
from integrate.handler import handler as integrate
from transform.handler import handler as transform
from validate.handler import handler as validate
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
