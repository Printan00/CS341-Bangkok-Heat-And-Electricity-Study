"""Build small .xlsx files for tests (openpyxl is a test-only dependency)."""
import io
import zipfile

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


def rezip(data, edit=None, add=None):
    """Copy an .xlsx (a zip). edit: {member: bytes -> bytes or None to drop}; add: {member: bytes}."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(out, "w") as dst:
        for name in src.namelist():
            body = src.read(name)
            if edit and name in edit:
                body = edit[name](body)
            if body is not None:
                dst.writestr(name, body)
        for name, body in (add or {}).items():
            dst.writestr(name, body)
    return out.getvalue()
