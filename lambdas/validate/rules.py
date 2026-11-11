"""Happy Home validation rules V01-V14 (reports/validation_rules.md).

FAIL (V01, V02 blank, V05) sends the row to quarantine. Everything else is a WARN: the row
passes with the rule id in dq_flags, and V07/V14 switch off usable_q1..q3 for the questions
that need the missing answers. Validate never edits a value; Transform does that.
"""
import math

from common.answers import burden, is_blank, key
from common.survey import a12, bills, multi, number, single, state, whole_number

FAIL, WARN = "FAIL", "WARN"
QUESTIONS = ("q1", "q2", "q3")


class Row:
    def __init__(self, num, values):
        self.source_row = num
        self.values = values
        self.violations = []  # (rule, level, message)
        self.usable = {q: True for q in QUESTIONS}
        self.household_code = None
        self.community_key = None
        self.community_source = None
        self.community_suggested = None
        self.a12_unbanded = None
        self.coords = None  # (lat, lon) when present and inside the bbox

    def add(self, rule, level, message):
        self.violations.append((rule, level, message))

    @property
    def failed(self):
        return any(level == FAIL for _, level, _ in self.violations)

    @property
    def dq_flags(self):
        return sorted({rule for rule, level, _ in self.violations if level == WARN})


def required_columns(c):
    cols = [c["id_column"], c["community_column"], c["lat_column"], c["lon_column"]]
    for q in c["questions"].values():
        cols.append(q["column"])
        cols += [o["column"] for o in q.get("options", {}).values()]
    for section in c["mandatory_sections"].values():
        cols += section
    return list(dict.fromkeys(cols))


def batch_errors(sheets, c):
    """Problems that stop the whole file (it cannot be checked row by row)."""
    sheet = sheets.get(c["data_sheet"])
    if sheet is None:
        return ["ไม่พบชีต %s" % c["data_sheet"]]
    missing = [col for col in required_columns(c) if col not in sheet.header]
    errors = []
    if missing:
        errors.append("ไม่พบคอลัมน์ที่กฎต้องใช้ %d คอลัมน์ เช่น %s" % (len(missing), ", ".join(missing[:3])))
    if not sheet.rows:
        errors.append("ไม่มีแถวข้อมูล")
    return errors


# ---------- rules ----------

def v01_ids(rows, c):
    seen = {}
    for r in rows:
        v = r.values.get(c["id_column"])
        r.household_code = None if is_blank(v) else str(v).strip()
        if r.household_code:
            seen.setdefault(r.household_code, []).append(r)
    for r in rows:
        if r.household_code is None:
            r.add("V01", FAIL, "รหัสครัวเรือนว่าง")
        elif len(seen[r.household_code]) > 1:
            # we cannot tell which copy is right, so every copy goes to quarantine
            r.add("V01", FAIL, "รหัสครัวเรือนซ้ำ %d แถว" % len(seen[r.household_code]))


def v02_community(r, c):
    v = r.values.get(c["community_column"])
    if is_blank(v):
        r.add("V02", FAIL, "ชื่อชุมชนว่าง")
        return
    m = {key(k): val for k, val in c["community_map"].items()}
    if key(v) in m:
        r.community_key, r.community_source = m[key(v)], "label"
    else:
        r.community_key, r.community_source = "unknown", "unknown"
        r.add("V02", WARN, "ชื่อชุมชนจัดกลุ่มไม่ได้ (community_key = unknown)")


def v03_allowed(r, c):
    bad = []
    for g in c["groups"].values():
        for code in g["items"]:
            if code == "A12":
                continue  # V05/V06 handle household size
            if state(r.values, c, code) == "invalid":
                bad.append(code)
    if bad:
        r.add("V03", WARN, "คำตอบไม่อยู่ในตัวเลือกของแบบสอบถาม: %s" % ", ".join(bad))


def v04_coords(r, c):
    lat, lon = number(r.values.get(c["lat_column"])), number(r.values.get(c["lon_column"]))
    if lat is None or lon is None:
        r.add("V04", WARN, "ไม่มีพิกัด")
        return
    b = c["bbox"]
    if not (b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]):
        r.add("V04", WARN, "พิกัดอยู่นอกกรอบกรุงเทพฯ")
        return
    r.coords = (lat, lon)


def v05_v06_household_size(r, c):
    _, st = a12(r.values, c)
    if st == "zero":
        r.add("V05", FAIL, "จำนวนสมาชิก (A12) = 0")
    elif st == "unbanded":
        r.a12_unbanded = whole_number(r.values.get(c["questions"]["A12"]["column"]))
        r.add("V06", WARN, "จำนวนสมาชิก (A12) เป็นตัวเลข ไม่ใช่ช่วง: Transform จัดช่วงให้")
    elif st == "invalid":
        r.add("V06", WARN, "จำนวนสมาชิก (A12) อ่านไม่ได้ นับเป็นค่าหาย")


def v07_unfinished(r, c):
    def answered(cols):
        return any(not is_blank(r.values.get(col)) for col in cols)

    s = c["mandatory_sections"]
    if not answered(s["B"] + s["C"] + s["E"]):
        r.add("V07", WARN, "สัมภาษณ์หยุดก่อนส่วน B: ใช้กับ Q1-Q3 ไม่ได้")
        for q in QUESTIONS:
            r.usable[q] = False
    elif not answered(s["E"]):
        r.add("V07", WARN, "สัมภาษณ์หยุดก่อนส่วน E")


def v08_v09_v10_bills(r, c):
    income, normal, summer = bills(r.values, c)
    if normal and summer:
        if summer[0] < normal[0]:
            r.add("V08", WARN, "ช่วงค่าไฟหน้าร้อนต่ำกว่าช่วงปกติ")
        inc, _ = single(r.values, c, "E1.3")
        if inc == "ไม่เพิ่ม" and summer[0] > normal[0]:
            r.add("V09", WARN, "ตอบว่าค่าไฟไม่เพิ่ม แต่ช่วงค่าไฟหน้าร้อนสูงกว่าช่วงปกติ")
    if income and summer:
        bmin, _ = burden(summer, income)
        if bmin >= c["thresholds"]["burden_implausible"]:
            r.add("V10", WARN, "ภาระค่าไฟต่ำสุด >= %d%% ของรายได้: ควรตรวจซ้ำ"
                  % round(c["thresholds"]["burden_implausible"] * 100))


def v11_aircon(r, c):
    coping, _ = multi(r.values, c, "C2.7")
    appliances, _ = multi(r.values, c, "E2.1")
    if coping.get("เปิดแอร์") == 1 and appliances.get("เครื่องปรับอากาศ") == 0:
        r.add("V11", WARN, "ตอบว่าเปิดแอร์ตอนร้อน แต่ไม่มีเครื่องปรับอากาศ")


def v12_exclusive_none(r, c):
    hit = []
    for code, none in c["exclusive_none"].items():
        flags, _ = multi(r.values, c, code)
        if flags.get(none) == 1 and any(f == 1 for lab, f in flags.items() if lab != none):
            hit.append(code)
    if hit:
        r.add("V12", WARN, "เลือก 'ไม่มี' พร้อมตัวเลือกอื่น: %s" % ", ".join(hit))


def v13_retrofit(r, c):
    ans, _ = single(r.values, c, "C2.8")
    detail, _ = multi(r.values, c, "C2.8_detail")
    if ans == "ไม่เคย" and any(f == 1 for f in detail.values()):
        r.add("V13", WARN, "ตอบว่าไม่เคยปรับปรุงบ้านลดความร้อน แต่มีวิธีที่ปรับปรุง")


def v14_usable(r, c):
    missing = []
    for g in c["groups"].values():
        gone = [code for code in g["core"] if state(r.values, c, code) != "ok"]
        if gone:
            missing += gone
            for q in g["used_by"]:
                r.usable[q] = False
    if missing:
        r.add("V14", WARN, "ข้อหลักว่างหรือผิด: %s" % ", ".join(missing))


# ---------- community suggestion from coordinates (T04, D5) ----------

def metres(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def centre(points):
    return sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)


def suggest_communities(rows, c):
    """Suggest a community for unmapped rows; WARN when a mapped row sits clearly in another community.

    Suggest C when the nearest mapped house of C is <= near_max metres away and the centre point
    (mean coordinate of the mapped houses) of every other community is >= other_min metres away.
    A person decides: the suggestion never fills community_key.
    """
    lim = c["community_suggest_m"]
    refs = [r for r in rows if r.coords and r.community_source == "label"]
    names = sorted({r.community_key for r in refs})
    centres = {n: centre([r.coords for r in refs if r.community_key == n]) for n in names}
    for r in rows:
        if not r.coords or r.community_key is None:
            continue
        pick = []
        for n in names:
            d = [metres(r.coords, o.coords) for o in refs if o is not r and o.community_key == n]
            if d and min(d) <= lim["near_max"] and all(
                    metres(r.coords, centres[m]) >= lim["other_min"] for m in names if m != n):
                pick.append(n)
        if len(pick) != 1:
            continue
        if r.community_source == "unknown":
            r.community_suggested = pick[0]
        elif pick[0] != r.community_key:
            r.add("V02", WARN, "พิกัดอยู่ใกล้ชุมชนอื่นมากกว่าชื่อที่ตอบ")


def validate(sheets, c):
    """-> (batch errors, [Row]). Rows are empty when the file cannot be checked."""
    errors = batch_errors(sheets, c)
    if errors:
        return errors, []
    rows = [Row(num, values) for num, values in sheets[c["data_sheet"]].rows]
    v01_ids(rows, c)
    for r in rows:
        v02_community(r, c)
        v03_allowed(r, c)
        v04_coords(r, c)
        v05_v06_household_size(r, c)
        v07_unfinished(r, c)
        v08_v09_v10_bills(r, c)
        v11_aircon(r, c)
        v12_exclusive_none(r, c)
        v13_retrofit(r, c)
        v14_usable(r, c)
    suggest_communities(rows, c)
    return [], rows
