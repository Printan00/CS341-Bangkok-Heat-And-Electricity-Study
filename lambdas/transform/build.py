"""Happy Home transform rules T01-T12 (reports/validation_rules.md): one passed raw row -> one trusted row.

Only the columns in contracts/trusted_happy_home.json are produced (an allowlist), so coordinates,
community name text, interviewer code and every other raw column never reach trusted/.
"""
from common.answers import burden, burden_class, is_blank
from common.survey import a12, bills, multi, single, size_band

HEAT_LEVEL = {"ร้อนมากทุกวัน": 3, "ร้อนบ่อย": 2, "ร้อนบางวัน": 1, "ไม่ค่อยร้อน": 0}
HEAT_EFFECTS = ["นอนไม่หลับ", "อยู่ในบ้านไม่สบาย", "ปวดหัว/อ่อนเพลีย", "ทำงานลำบาก", "เด็กเรียนหนังสือลำบาก"]
INCOME_HIT = {"มาก": 2, "บางส่วน": 1}       # D1.1 heat
HEALTH_HIT = {"เคย": 1}                     # D2.1 heat
STRESS = {"มาก": 2, "ปานกลาง": 1}           # D2.2 heat
HOUSING = {"B4": {"สังกะสี/เมทัลชีท"}, "B6": {"ไม่มี"}, "B7": {"ไม่มี"}, "B8": {"ไม่ดี"}, "B9": {"น้อย", "ไม่มีเลย"}}
VULNERABLE = ["ผู้สูงอายุ", "ผู้พิการ", "ผู้ป่วยเรื้อรัง", "ผู้ป่วยติดเตียง"]


DASHES = "-\u2010\u2011\u2012\u2014\u2212"


def t01(values, c, code):
    """T01: the questionnaire spelling of a valid answer; otherwise the answer trimmed with '–' dashes."""
    ans, _ = single(values, c, code)
    if ans is not None:
        return ans
    v = values.get(c["questions"][code]["column"])
    if is_blank(v):
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return "".join("\u2013" if ch in DASHES else ch for ch in str(v).strip())


def clean(values, c, code):
    """T02: answer for analysis, None when blank, not a questionnaire answer, or unsure."""
    ans, _ = single(values, c, code)
    return None if ans is None or ans in c["null_answers"] else ans


def housing_score(values, c):
    """T09: 1 point per heat-prone housing answer; null when fewer than the minimum are answered clearly."""
    answered = score = 0
    for code, risky in HOUSING.items():
        ans = clean(values, c, code)
        if ans is None:
            continue
        answered += 1
        score += ans in risky
    return (score if answered >= c["thresholds"]["housing_min_answered"] else None), answered


def heat_impact(values, c):
    """T10 heat_impact_score 0-13; null when C2.1 or C2.5 (the core items) is missing."""
    level = clean(values, c, "C2.1")
    effects, st = multi(values, c, "C2.5")
    if level is None or st != "ok":
        return None
    score = HEAT_LEVEL[level] + sum(effects.get(e) == 1 for e in HEAT_EFFECTS)
    score += INCOME_HIT.get(clean(values, c, "D1.1H"), 0)
    score += HEALTH_HIT.get(clean(values, c, "D2.1H"), 0)
    score += STRESS.get(clean(values, c, "D2.2H"), 0)
    return score


def coping_limit(values, c):
    """T10 coping_limit_score 0-6; null when C2.7 or A14 (the core items) is missing."""
    tenure = clean(values, c, "A14")
    coping, st = multi(values, c, "C2.7")
    if tenure is None or st != "ok":
        return None
    members, _ = multi(values, c, "A13")
    barriers, _ = multi(values, c, "B12")
    return sum([
        tenure != "เป็นเจ้าของเอง",
        clean(values, c, "A10") == "ไม่มี",
        barriers.get("ไม่มีงบประมาณ") == 1,
        any(members.get(m) == 1 for m in VULNERABLE),
        clean(values, c, "G8") == "ไม่มี",
        coping.get("ไม่มีวิธีรับมือ") == 1,
    ])


def level(score, levels):
    if score is None:
        return None
    for name, lo, hi in levels:
        if lo <= score <= hi:
            return name
    return None


def trusted_row(values, passed, manifest, c):
    """values: raw row; passed: this row's entry in manifest["passed"] (Validate's decisions)."""
    t = c["thresholds"]
    out = {
        "household_code": passed["household_code"],
        "community_key": passed["community_key"],
        "community_source": passed["community_source"],
        "community_suggested": passed["community_suggested"],
    }
    for code, q in c["questions"].items():
        if q["kind"] == "single":
            out[q["name"]] = t01(values, c, code)
            out[q["name"] + "_clean"] = None if code == "A12" else clean(values, c, code)
        else:
            flags, _ = multi(values, c, code)
            for lab, o in q["options"].items():
                out[o["name"]] = flags[lab] if flags[lab] in (0, 1) else None

    # T03 household size band
    size, st = a12(values, c)
    if st == "unbanded":
        size = size_band(passed["a12_unbanded"], c["household_size_bands"])
    out["a12_household_size_clean"] = size
    out["household_size_band"] = size

    # T06 band -> order + lower/upper bound; T07 burden (summer bill is the main one)
    income, normal, summer = bills(values, c)
    for name, b in (("income", income), ("bill_normal", normal), ("bill_summer", summer)):
        out[name + "_ord"], out[name + "_min"], out[name + "_max"] = b if b else (None, None, None)
    for prefix, bill in (("burden", summer), ("burden_normal", normal)):
        lo, hi = burden(bill, income) if bill and income else (None, None)
        out[prefix + "_min"], out[prefix + "_max"] = lo, hi
    lo, hi = out["burden_min"], out["burden_max"]
    out["burden_class"] = burden_class(lo, hi, t["burden_high"]) if lo is not None else None
    out["burden_class_6pct"] = burden_class(lo, hi, t["burden_high_sensitivity"]) if lo is not None else None

    # T08 air conditioner
    appliances, st = multi(values, c, "E2.1")
    ac = appliances.get("เครื่องปรับอากาศ")
    out["has_aircon"] = None if st != "ok" or ac is None else ac == 1

    # T09, T10 scores
    out["housing_heat_score"], out["housing_items_answered"] = housing_score(values, c)
    out["heat_impact_score"] = heat_impact(values, c)
    out["heat_impact_level"] = level(out["heat_impact_score"], t["heat_impact_levels"])
    cl = coping_limit(values, c)
    out["coping_limit_score"] = cl
    out["coping_limited"] = None if cl is None else cl >= t["coping_limited_min"]

    # T11 usable flags (decided in Validate by V07/V14), dq flags, T12 lineage
    for q in ("usable_q1", "usable_q2", "usable_q3"):
        out[q] = passed[q]
    out["dq_flags"] = ",".join(passed["dq_flags"])
    out["source_dataset"] = manifest["source"]
    out["batch_id"] = manifest["batch_id"]
    out["source_file_sha256"] = manifest["source_file_sha256"]
    out["source_row"] = passed["source_row"]
    return out


def trusted_rows(sheet, manifest, c):
    """All passed rows of the batch, matched to the raw sheet by source_row."""
    by_row = dict(sheet.rows)
    out = []
    for p in manifest["passed"]:
        values = by_row.get(p["source_row"])
        if values is None or str(values.get(c["id_column"]) or "").strip() != p["household_code"]:
            raise ValueError("raw row %s does not match the Validate manifest" % p["source_row"])
        out.append(trusted_row(values, p, manifest, c))
    return out
