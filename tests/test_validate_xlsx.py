"""The standard-library .xlsx reader used inside the Lambda."""
from xlsx_helper import xlsx_bytes

import xlsx


def test_reads_sheets_in_order_with_typed_values_and_blanks():
    data = xlsx_bytes({
        "Data": [["id", "name", "n", "x", "ok"], ["HH-1", "หลังแฟลต", 3, 2.75, True], ["HH-2", None, None, 2.0, False]],
        "Settings": [["setting", "value"], ["GPS_DECIMALS", 3]],
    })
    sheets = xlsx.read_workbook(data)
    assert list(sheets) == ["Data", "Settings"]
    t = sheets["Data"]
    assert t.header == ["id", "name", "n", "x", "ok"]
    assert t.rows[0] == {"id": "HH-1", "name": "หลังแฟลต", "n": 3, "x": 2.75, "ok": True}
    assert t.rows[1] == {"id": "HH-2", "name": None, "n": None, "x": 2, "ok": False}


def test_header_names_are_made_unique_like_the_contract_expects():
    # Repeated labels get ".1", ".2"; blank headers become "Unnamed: <position>"
    data = xlsx_bytes({"Data": [["ความร้อน", "ความร้อน", None, "ความร้อน"], [1, 2, 3, 4]]})
    t = xlsx.read_workbook(data)["Data"]
    assert t.header == ["ความร้อน", "ความร้อน.1", "Unnamed: 2", "ความร้อน.2"]
    assert t.rows[0]["Unnamed: 2"] == 3


def test_sheet_with_header_only_has_no_rows():
    t = xlsx.read_workbook(xlsx_bytes({"Data": [["a", "b"]]}))["Data"]
    assert t.header == ["a", "b"] and t.rows == []
