"""Minimal .xlsx reader using only the standard library (the Lambda has no openpyxl/pandas).

Reads cell values only (no formulas or styles). The first row of each sheet is the header;
repeated header labels get ".1", ".2" and blank ones "Unnamed: <position>", so every column
has a unique name (the contracts in contracts/*.json use these names).
"""
import io
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET

from core import Table

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"


def _col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def _text(node):
    return "".join(t.text or "" for t in node.iter("{%s}t" % NS["m"]))


def _number(s):
    f = float(s)
    return int(f) if f.is_integer() and re.fullmatch(r"-?\d+(\.0+)?", s) else f


def _cell_value(c, shared):
    t = c.get("t")
    if t == "inlineStr":
        node = c.find("m:is", NS)
        return _text(node) if node is not None else None
    v = c.find("m:v", NS)
    if v is None or v.text is None:
        return None
    if t == "s":
        return shared[int(v.text)]
    if t == "b":
        return v.text == "1"
    if t in ("str", "e"):
        return v.text
    return _number(v.text)


def unique_header(raw):
    seen, counts, out = set(), {}, []
    for i, h in enumerate(raw):
        name = "Unnamed: %d" % i if h is None or str(h) == "" else str(h)
        if name in seen:
            k = counts.get(name, 1)
            while "%s.%d" % (name, k) in seen:
                k += 1
            counts[name] = k + 1
            name = "%s.%d" % (name, k)
        seen.add(name)
        out.append(name)
    return out


def _sheet_rows(xml, shared):
    rows = []
    for r in ET.fromstring(xml).iterfind("m:sheetData/m:row", NS):
        cells = {}
        for c in r.iterfind("m:c", NS):
            cells[_col_index(c.get("r"))] = _cell_value(c, shared)
        width = max(cells) + 1 if cells else 0
        rows.append([cells.get(i) for i in range(width)])
    return rows


def read_workbook(data):
    """bytes of an .xlsx file -> {sheet name: Table} in workbook order."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = set(z.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            shared = [_text(si) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iterfind("m:si", NS)]
        rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).iter(PKG_REL)}
        out = {}
        for s in ET.fromstring(z.read("xl/workbook.xml")).iterfind("m:sheets/m:sheet", NS):
            target = rels[s.get(REL)]
            path = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            rows = _sheet_rows(z.read(path), shared)
            if not rows:
                out[s.get("name")] = Table([], [])
                continue
            header = unique_header(rows[0])
            body = []
            for r in rows[1:]:
                if all(v is None for v in r):
                    continue  # Excel keeps formatted-but-empty rows; they are not records
                body.append({h: (r[i] if i < len(r) else None) for i, h in enumerate(header)})
            out[s.get("name")] = Table(header, body)
        return out
