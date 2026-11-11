"""The contracts stay consistent with each other and with the privacy rule (allowlist, no coordinates)."""
from common import lake
from common.answers import burden, burden_class, canonical, key
from common.survey import size_band


def test_trusted_and_curated_are_allowlists_without_private_columns():
    trusted = lake.contract("trusted_happy_home")
    curated = lake.contract("curated_happy_home_household")
    for con in (trusted, curated):
        names = [c["name"] for c in con["columns"]]
        assert len(names) == len(set(names))
        assert not set(names) & set(con["forbidden_columns"])
        assert not [n for n in names if "lat" in n.split("_") or "lon" in n.split("_") or "interviewer" in n]
    t = {c["name"]: c for c in trusted["columns"]}
    shared = [c for c in curated["columns"] if c["name"] in t]
    assert all(c == t[c["name"]] for c in shared)  # same type and meaning in both tables


def test_every_question_maps_to_trusted_columns(contract):
    trusted = {c["name"] for c in lake.contract("trusted_happy_home")["columns"]}
    for code, q in contract["questions"].items():
        if q["kind"] == "single":
            assert {q["name"], q["name"] + "_clean"} <= trusted, code
        else:
            assert {o["name"] for o in q["options"].values()} <= trusted, code


def test_groups_and_rules_use_known_questions(contract):
    codes = set(contract["questions"])
    for g in contract["groups"].values():
        assert set(g["items"]) <= codes and set(g["core"]) <= set(g["items"])
    assert set(contract["exclusive_none"]) <= codes
    for code, none in contract["exclusive_none"].items():
        assert none in contract["questions"][code]["options"]


def test_c2_8_detail_is_the_heat_copy(contract):
    detail = contract["questions"]["C2.8_detail"]
    assert detail["column"].endswith(".1")  # the flood copy (C1.11) has no suffix
    assert "ติดฉนวน" in detail["options"] and "ยกพื้น" not in detail["options"]


def test_band_tables_follow_the_spec(contract):
    assert contract["income_bands"][0][1:] == [2500, 5000]  # D1 floor
    assert contract["income_bands"][-1][1:] == [50001, 100000]  # D1 cap
    assert contract["bill_bands"][-1][1:] == [3001, 6000]  # D1 cap
    assert contract["thresholds"]["burden_high"] == 0.10 and contract["thresholds"]["burden_implausible"] == 0.50


def test_spec_burden_example(contract):
    income = (2, 5001, 10000)
    bill = (3, 1001, 2000)
    lo, hi = burden(bill, income)
    assert round(lo, 2) == 0.10 and round(hi, 2) == 0.40
    assert burden_class(lo, hi, 0.10) == "high"


def test_answer_matching_ignores_spacing_and_dash_style():
    assert key("5,001-10,000 บาท") == key("5,001–10,000 บาท")
    assert canonical(" ทุกคนพอๆกัน ", ["ทุกคนพอ ๆ กัน"]) == "ทุกคนพอ ๆ กัน"
    assert canonical("ไม่รู้", ["มี", "ไม่มี"]) is None
    assert [size_band(n, ["1", "2–3", "4–5", "6+"]) for n in (1, 2, 3, 5, 6, 12)] == \
        ["1", "2–3", "2–3", "4–5", "6+", "6+"]
