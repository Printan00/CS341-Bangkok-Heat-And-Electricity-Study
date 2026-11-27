"""gee_lst source (community LST CSV): Validate G01-G10 -> Transform -> Integrate -> Verify -> community_dim,
and the Happy Home join of the published community_dim into happy_home_risk (D21)."""
import json

import pytest

from check_batch.handler import handler as check_batch
from common import lake, parquet
from hh_factory import household, town, workbook
from integrate.handler import handler as integrate
from integrate.scoring import lst_score
from transform.handler import handler as transform
from validate.handler import handler as validate
from verify.handler import VerifyFailed, handler as verify

GEE = "gee_lst-0123456789ab"
HH = "happy_home-0123456789ab"
GQ = "quarantine/gee_lst/%s/" % GEE
HEADER = ["community", "n_households", "lst_mean_c", "n_scenes", "period", "buffer_m", "source"]
GOOD = [["คนรักถิ่น", "50", "41.2", "14", "2026-03-01..2026-05-31", "300", "landsat8/9_c02_l2_ST_B10"],
        ["หลังแฟลต", "31", "39.8", "14", "2026-03-01..2026-05-31", "300", "landsat8/9_c02_l2_ST_B10"]]


def csv_bytes(rows, header=HEADER):
    lines = [",".join(header)] + [",".join(r) for r in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


def ingest_gee(s3, rows=GOOD, header=HEADER, data=None, batch=GEE):
    s3.objects["raw/gee_lst/%s/gee_lst_community.csv" % batch] = data or csv_bytes(rows, header)


def run_gee(s3, rows=GOOD, batch=GEE):
    ingest_gee(s3, rows, batch=batch)
    ev = {"batch_id": batch}
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


def report(s3):
    return json.loads(s3.objects[GQ + "dq_report.json"])


# ---------- Validate G01-G10 ----------

def test_good_csv_passes_with_both_communities(s3):
    ingest_gee(s3)
    out = validate({"batch_id": GEE}, None)
    assert (out["valid"], out["rows_passed"], out["rows_quarantined"]) == (True, 2, 0)
    man = json.loads(s3.objects[GQ + "manifest.json"])
    assert man["status"] == "passed"
    assert [p["community_key"] for p in man["passed"]] == ["คนรักถิ่น", "หลังแฟลต"]
    assert report(s3)["batch_warnings"] == []


@pytest.mark.parametrize("index, value, rule", [
    (0, "ชุมชนอื่น", "G04"),                       # not a Happy Home community key
    (2, "", "G06"),                                # no clear pixels -> blank LST from the script
    (2, "95", "G06"),                              # not a plausible land surface temperature
    (3, "0", "G07"),                               # no scenes
    (3, "2.5", "G07"),
    (4, "2026-05-31..2026-03-01", "G08"),          # start after end
    (5, "-1", "G08"),
])
def test_bad_value_quarantines_the_row(s3, index, value, rule):
    rows = [list(r) for r in GOOD]
    rows[1][index] = value
    ingest_gee(s3, rows)
    out = validate({"batch_id": GEE}, None)
    assert (out["valid"], out["rows_passed"], out["rows_quarantined"]) == (True, 1, 1)
    man = json.loads(s3.objects[GQ + "manifest.json"])
    assert man["quarantined"][0]["rules"] == [rule]
    assert any(w.startswith("G10") for w in report(s3)["batch_warnings"])  # หลังแฟลต now has no LST


def test_duplicate_community_quarantines_every_copy(s3):
    ingest_gee(s3, [GOOD[0], GOOD[0], GOOD[1]])
    out = validate({"batch_id": GEE}, None)
    assert (out["rows_passed"], out["rows_quarantined"]) == (1, 2)
    assert report(s3)["rules"] == {"G05": {"FAIL": 2}}


def test_coordinate_column_stops_the_batch_and_keeps_no_rows(s3):
    header = HEADER + ["lat"]
    ingest_gee(s3, [r + ["13.88"] for r in GOOD], header=header)
    out = validate({"batch_id": GEE}, None)
    assert out["valid"] is False and report(s3)["batch_errors"][0].startswith("G03")
    assert s3.objects[GQ + "rows.jsonl"] == b""
    assert b"13.88" not in b"".join(v for k, v in s3.objects.items() if k.startswith(GQ))


def test_missing_column_and_unreadable_file_stop_the_batch(s3):
    ingest_gee(s3, [r[:-1] for r in GOOD], header=HEADER[:-1])
    assert validate({"batch_id": GEE}, None)["valid"] is False
    assert report(s3)["batch_errors"][0].startswith("G02")
    ingest_gee(s3, data=b"\xff\xfe\x00broken")
    assert validate({"batch_id": GEE}, None)["valid"] is False
    assert report(s3)["batch_errors"][0].startswith("G01")


def test_mixed_periods_stop_the_batch(s3):
    rows = [list(r) for r in GOOD]
    rows[1][4] = "2025-03-01..2025-05-31"
    ingest_gee(s3, rows)
    assert validate({"batch_id": GEE}, None)["valid"] is False
    assert report(s3)["batch_errors"][0].startswith("G09")


def test_gee_raw_file_must_be_a_csv(s3):
    s3.objects["raw/gee_lst/%s/gee.xlsx" % GEE] = b"x"
    with pytest.raises(FileNotFoundError, match=".csv"):
        validate({"batch_id": GEE}, None)


# ---------- Transform / Integrate / Verify -> community_dim ----------

def test_lst_score_uses_the_fixed_30_45_range():
    rng = lake.contract("gee_lst")["lst_score_c"]
    assert rng == [30.0, 45.0]
    assert [lst_score(v, rng) for v in (25.0, 30.0, 37.5, 45.0, 50.0)] == [0.0, 0.0, 0.5, 1.0, 1.0]
    assert lst_score(None, rng) is None


def test_gee_batch_publishes_community_dim(s3):
    out = run_gee(s3)
    assert out["verified"] is True
    trusted = parquet.read(s3.objects[lake.trusted_key(GEE)])
    assert trusted.schema.equals(parquet.schema(lake.contract("trusted_gee_lst")))
    dim = table(s3, lake.curated_key("community_dim"))
    assert [c["name"] for c in lake.contract("curated_community_dim")["columns"]] == list(dim[0])
    got = {d["community_key"]: (d["lst_mean_c"], d["lst_score"], d["n_scenes"], d["period_end"]) for d in dim}
    assert got == {"คนรักถิ่น": (41.2, pytest.approx(11.2 / 15), 14, "2026-05-31"),
                   "หลังแฟลต": (39.8, pytest.approx(9.8 / 15), 14, "2026-05-31")}
    marker = json.loads(s3.objects[lake.success_key(GEE)])
    assert marker["table"] == "community_dim" and marker["community_dim_rows"] == 2


def test_gee_verify_refuses_a_wrong_lst_score(s3):
    ingest_gee(s3)
    ev = {"batch_id": GEE}
    for step in (validate, transform, integrate):
        ev = step(ev, None)
    key = lake.staging_key(GEE, "community_dim")
    rows = table(s3, key)
    rows[0]["lst_score"] = 0.99
    s3.objects[key] = parquet.to_bytes(rows, lake.contract("curated_community_dim"))
    with pytest.raises(VerifyFailed, match="lst_score"):
        verify(ev, None)
    assert lake.curated_key("community_dim") not in s3.objects


def test_published_gee_batch_is_skipped_by_check_batch(s3):
    run_gee(s3)
    assert check_batch({"batch_id": GEE}, None)["already_done"] is True


# ---------- Happy Home joins community_dim (D21) ----------

def test_households_get_their_community_lst_and_unknown_gets_null(s3):
    run_gee(s3)
    rows = town(4) + [household(99, community="F")]  # "F" cannot be mapped -> community_key unknown
    run_hh(s3, rows)
    risk = {r["household_code"]: r for r in table(s3, lake.curated_key("happy_home_risk"))}
    assert (risk["HH-000001"]["lst_mean_c"], risk["HH-000001"]["lst_batch_id"]) == (41.2, GEE)  # คนรักถิ่น
    assert risk["HH-000002"]["lst_mean_c"] == 39.8  # หลังแฟลต
    assert risk["HH-000002"]["lst_score"] == pytest.approx(9.8 / 15)
    assert (risk["HH-000099"]["lst_mean_c"], risk["HH-000099"]["lst_score"]) == (None, None)
    marker = json.loads(s3.objects[lake.success_key(HH)])
    assert marker["lst_batch_ids"] == [GEE]


def test_lst_is_not_part_of_risk_score(s3):
    run_hh(s3, town(4))
    before = {r["household_code"]: r["risk_score"] for r in table(s3, lake.curated_key("happy_home_risk"))}
    run_gee(s3)
    run_hh(s3, town(4))
    after = table(s3, lake.curated_key("happy_home_risk"))
    assert {r["household_code"]: r["risk_score"] for r in after} == before
    assert all(r["lst_mean_c"] is not None for r in after)


def test_happy_home_without_gee_has_null_lst(s3):
    run_hh(s3, town(4))
    risk = table(s3, lake.curated_key("happy_home_risk"))
    assert all(r["lst_mean_c"] is None and r["lst_score"] is None and r["lst_batch_id"] is None for r in risk)


@pytest.mark.parametrize("change", [
    lambda r: r.update(lst_mean_c=50.0, lst_score=1.0),   # not the community's value
    lambda r: r.update(lst_score=0.1),                    # not the fixed scale
    lambda r: r.update(lst_batch_id=None),
])
def test_verify_refuses_a_wrong_lst_join(s3, change):
    run_gee(s3)
    s3.objects["raw/happy_home/%s/survey.xlsx" % HH] = workbook(town(4))
    ev = {"batch_id": HH}
    for step in (validate, transform, integrate):
        ev = step(ev, None)
    key = lake.staging_key(HH, "happy_home_risk")
    rows = table(s3, key)
    change(rows[0])
    s3.objects[key] = parquet.to_bytes(rows, lake.contract("curated_happy_home_risk"))
    with pytest.raises(VerifyFailed, match="published community_dim|lst_score"):
        verify(ev, None)
    assert lake.curated_key("happy_home_risk") not in s3.objects
