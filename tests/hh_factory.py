"""Synthetic Happy Home workbooks for tests: one 'ordinary' household per row, edited per test."""
from common import lake
from validate.rules import required_columns
from xlsx_helper import xlsx_bytes

C = lake.contract("happy_home")
Q = C["questions"]

SINGLE = {
    "A6": "รายได้สม่ำเสมอ", "A7": "10,001–20,000 บาท", "A8": "10,001–20,000 บาท", "A10": "มี",
    "A11": "ไม่มี", "A12": "2–3", "A14": "เป็นเจ้าของเอง",
    "B1": "บ้านเดี่ยว", "B3": "คอนกรีต", "B4": "กระเบื้อง", "B6": "มี", "B7": "มี", "B8": "ดี", "B9": "มาก",
    "C2.1": "ร้อนบ่อย", "C2.4": "ห้องนอน", "C2.6": "ผู้สูงอายุ", "C2.8": "ไม่เคย",
    "D1.1H": "บางส่วน", "D2.1H": "ไม่เคย", "D2.2H": "เล็กน้อย",
    "E1.1": "1,001–2,000 บาท", "E1.2": "1,001–2,000 บาท", "E1.3": "เพิ่มเล็กน้อย",
    "E2.4": "พัดลม", "E2.6": "ไม่เคย", "G8": "ครอบครัว/ญาติ",
}
MULTI_ON = {"A13": ["ผู้สูงอายุ"], "B11": ["ร้อนมาก"], "B12": ["พื้นที่จำกัด"], "C2.5": ["นอนไม่หลับ"],
            "C2.7": ["เปิดพัดลม"], "E2.1": ["พัดลม", "ตู้เย็น"]}
# In Bangkok, ~100 m apart: community A around (13.880, 100.580), community B ~1 km east
A_POINT, B_POINT = (13.880, 100.580), (13.880, 100.590)


def col(code, option=None):
    return Q[code]["options"][option]["column"] if option else Q[code]["column"]


def household(i=1, community="ชุมชนคนรักถิ่น", point=A_POINT):
    row = {c: "x" for c in required_columns(C)}  # mandatory items answered
    row[C["id_column"]] = "HH-%06d" % i
    row[C["community_column"]] = community
    row[C["lat_column"]], row[C["lon_column"]] = point
    for code, ans in SINGLE.items():
        row[col(code)] = ans
    for code, q in Q.items():
        if q["kind"] != "multi":
            continue
        on = MULTI_ON.get(code, [])
        for lab, o in q["options"].items():
            row[o["column"]] = None if code == "C2.8_detail" else (1 if lab in on else 0)
        row[q["column"]] = None if code == "C2.8_detail" else " ".join(on)
    return row


def workbook(rows, header=None, sheet="Data"):
    header = header or required_columns(C)
    return xlsx_bytes({sheet: [header] + [[r.get(h) for h in header] for r in rows],
                       "Audit_log": [["event"]], "Settings": [["setting", "value"]]})


def town(n=10):
    """n ordinary households split between the two communities, each at its own point."""
    out = []
    for i in range(n):
        name, (lat, lon) = (("ชุมชนคนรักถิ่น", A_POINT) if i % 2 == 0 else ("ชุมชนหลังแฟลต", B_POINT))
        out.append(household(i + 1, name, (lat + 0.0002 * (i // 2), lon)))
    return out
