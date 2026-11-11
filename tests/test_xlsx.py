"""The standard-library .xlsx reader used by the Lambdas."""
import re

from common.xlsx import read_workbook, unique_header
from xlsx_helper import rezip, xlsx_bytes


def test_reads_values_and_keeps_excel_row_numbers():
    data = xlsx_bytes({"Data": [["id", "n", "x"], ["a", 1, 2.5], [None, None, None], ["b", "2", None]]})
    sheet = read_workbook(data)["Data"]
    assert sheet.header == ["id", "n", "x"]
    assert sheet.rows == [(2, {"id": "a", "n": 1, "x": 2.5}), (4, {"id": "b", "n": "2", "x": None})]


def test_repeated_and_blank_headers_get_pandas_names():
    assert unique_header(["a", "a", None, "a"]) == ["a", "a.1", "Unnamed: 2", "a.2"]


def test_cells_without_references_are_read_in_order():
    data = xlsx_bytes({"Data": [["a", "b"], [1, 2]]})

    def strip_refs(xml):
        return re.sub(rb' r="[A-Z]*[0-9]+"', b"", xml)

    data = rezip(data, edit={"xl/worksheets/sheet1.xml": strip_refs})
    assert read_workbook(data)["Data"].rows == [(2, {"a": 1, "b": 2})]
