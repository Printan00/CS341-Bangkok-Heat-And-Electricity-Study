"""Build small .xlsx files for tests (openpyxl is a test-only dependency)."""
import io

import openpyxl


def xlsx_bytes(sheets):
    """sheets: {sheet name: [header row, data row, ...]} -> .xlsx bytes."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
