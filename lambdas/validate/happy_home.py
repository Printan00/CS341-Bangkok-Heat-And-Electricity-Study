"""Happy Home (ThaiCI household survey) rules. See reports/validation_rules.md §3-§5."""
import re

from core import (Table, duplicate_content_mask, flag, flag_on, is_blank, load_contract, norm_label, run_batch,
                  text, to_number)

SOURCE = "happy_home"
HAZARDS = ("น้ำท่วม", "ความร้อน")


def validate(data, contract=None, batch_id=None):
    return run_batch(SOURCE, data, contract or load_contract(SOURCE), row_checks, enrich, batch_id)


def row_checks(t, c):
    """Run every rule whose contract keys are present."""
    out = []
    if "id_column" in c:
        out += check_id(t, c)
    if "community_map" in c:
        out += check_community(t, c)
    if "required" in c:
        out += check_required(t, c)
    if "allowed_values" in c:
        out += check_domain(t, c)
    if c.get("check_flags"):
        out += check_multiselect(t, c) + check_grid(t, c)
    if "skip_logic" in c:
        out += check_skip_logic(t, c)
    if "month_column" in c:
        out += check_month(t, c)
    return out + check_warnings(t, c)


def enrich(t, c):
    """Add the canonical community key used by Transform and Integrate."""
    if "community_map" not in c:
        return t
    keys = map_community(t, c)
    return Table(t.header + ["community_key"], [{**r, "community_key": k} for r, k in zip(t.rows, keys)])


def _f(t, c, mask, rule, sev, col, msg):
    return flag(t, mask, rule, sev, col, msg, id_col=c["id_column"])


# ---------- FAIL rules (row goes to quarantine) ----------

def check_id(t, c):
    col = c["id_column"]
    ids = t.column(col)
    bad = [is_blank(v) or not re.match(c["id_pattern"], str(v)) for v in ids]
    present = [v for v in ids if not is_blank(v)]
    dup = [not is_blank(v) and present.count(v) > 1 for v in ids]
    return (_f(t, c, bad, "R01", "FAIL", col, "id blank or wrong format")
            + _f(t, c, dup, "R02", "FAIL", col, "id duplicated in batch"))


def map_community(t, c):
    table = {k.strip(): v for k, v in c["community_map"].items()}
    return [None if is_blank(v) else table.get(str(v).strip()) for v in t.column(c["community_column"])]


def check_community(t, c):
    return _f(t, c, [k is None for k in map_community(t, c)], "R03", "FAIL", c["community_column"],
              "community_unmapped: label not in mapping table (likely the third community มิตรประชา; kept out of analysis)")


def check_required(t, c):
    out = []
    for col in c["required"]:
        out += _f(t, c, [is_blank(v) for v in t.column(col)], "R04", "FAIL", col, "required field blank")
    return out


def check_domain(t, c):
    out = []
    for col, allowed in c["allowed_values"].items():
        ok = {norm_label(a) for a in allowed}
        bad = [not is_blank(v) and norm_label(v) not in ok for v in t.column(col)]
        out += _f(t, c, bad, "R05", "FAIL", col, "value not in questionnaire options")
    return out


def _label(child, parent):
    """Option label of a 'parent/option' column; drops the '.1' suffix added to repeated names."""
    base = re.sub(r"\.\d+$", "", parent)
    return re.sub(r"\.\d+$", "", child[len(base) + 1:])


def _children(t, c):
    """parent column -> {option label: child column}.

    The contract can assign option columns explicitly (multiselect_overrides) when two questions
    share a parent label and the export gives their options the same prefix (C1.11 / C2.8).
    """
    overrides = c.get("multiselect_overrides", {})
    taken = {k for kids in overrides.values() for k in kids}
    groups = {p: {_label(k, p): k for k in kids} for p, kids in overrides.items()}
    for p in t.header:
        if p in groups:
            continue
        kids = {_label(k, p): k for k in t.header if k.startswith(p + "/") and k not in taken}
        if kids:
            groups[p] = kids
    return groups


def _is_grid(kids):
    return set(kids) == set(HAZARDS)


def check_multiselect(t, c):
    out = []
    for parent, kids in _children(t, c).items():
        if _is_grid(kids):
            continue
        bad = []
        for r in t.rows:
            answer = text(r.get(parent))
            nums = {label: to_number(r.get(col)) for label, col in kids.items()}
            nonbinary = any(n is not None and n not in (0, 1) for n in nums.values())
            on = [label for label, n in nums.items() if n == 1]
            mismatch = any(label not in answer for label in on) or (answer != "") != bool(on)
            bad.append(nonbinary or mismatch)
        out += _f(t, c, bad, "R06", "FAIL", parent, "multi-select flags not 0/1 or not matching answer text")
    return out


def check_grid(t, c):
    out = []
    for parent, kids in _children(t, c).items():
        if not _is_grid(kids):
            continue
        bad = []
        for r in t.rows:
            tokens = set(text(r.get(parent)).split())
            bad.append(not tokens <= set(HAZARDS)
                       or any((hz in tokens) != flag_on(r.get(kids[hz])) for hz in HAZARDS))
        out += _f(t, c, bad, "R07", "FAIL", parent, "grid text not matching flood/heat flags")
    return out


def check_skip_logic(t, c):
    out = []
    for rule in c["skip_logic"]:
        bad = [(text(r.get(rule["gate"])) == rule["gate_value"]) != (not is_blank(r.get(rule["follow"])))
               for r in t.rows]
        out += _f(t, c, bad, "R08", "FAIL", rule["follow"],
                  "follow-up answered/blank inconsistent with %s" % rule["gate"])
    return out


def check_month(t, c):
    def bad(v):
        s = text(v)
        return not re.fullmatch(r"\d{4}-\d{2}", s) or not (c["month_min"] <= s <= c["month_max"])

    col = c["month_column"]
    return _f(t, c, [bad(v) for v in t.column(col)], "R09", "FAIL", col,
              "interview month missing or outside survey window")


# ---------- WARN rules (row passes with dq_flags) ----------

def _band(v, bands):
    ix = {norm_label(b): i for i, b in enumerate(bands)}
    return -1 if is_blank(v) else ix.get(norm_label(v), -1)


def check_warnings(t, c):
    out = []
    rows = t.rows
    if "income_column" in c:
        inc = [_band(r.get(c["income_column"]), c["income_bands"]) for r in rows]
        normal = [_band(r.get(c["normal_bill_column"]), c["bill_bands"]) for r in rows]
        summer = [_band(r.get(c["summer_bill_column"]), c["bill_bands"]) for r in rows]
        top = len(c["bill_bands"]) - 1
        out += _f(t, c, [i == 0 and s == top for i, s in zip(inc, summer)], "W01", "WARN",
                  c["summer_bill_column"], "lowest income band with highest summer bill band")
        out += _f(t, c, [s >= 0 and n >= 0 and s < n for s, n in zip(summer, normal)], "W02", "WARN",
                  c["summer_bill_column"], "summer bill band lower than normal")
    if "lat_column" in c:
        y0, y1, x0, x1 = c["bbox"]

        def outside(r):
            lat, lon = to_number(r.get(c["lat_column"])), to_number(r.get(c["lon_column"]))
            return lat is None or lon is None or not (y0 <= lat <= y1 and x0 <= lon <= x1)

        out += _f(t, c, [outside(r) for r in rows], "W03", "WARN", c["lat_column"],
                  "coordinates blank or outside Bangkok bbox")
    for g in c.get("exclusive_none", []):
        out += _f(t, c, [flag_on(r.get(g["none"])) and any(flag_on(r.get(o)) for o in g["others"]) for r in rows],
                  "W04", "WARN", g["none"], "'none' selected together with other options")
    if "aircon_flag" in c:
        bad = [not flag_on(r.get(c["aircon_flag"]))
               and any(text(r.get(col)) == val for col, val in c["aircon_claims"].items()) for r in rows]
        out += _f(t, c, bad, "W05", "WARN", c["aircon_flag"],
                  "says air-conditioner drives the bill but has no air-conditioner")
    if "flood_never" in c:
        f = c["flood_never"]
        bad = [text(r.get(f["gate"])) == f["value"] and not is_blank(r.get(f["follow"])) for r in rows]
        out += _f(t, c, bad, "W06", "WARN", f["follow"], "never flooded but flood frequency answered")
    if "community_only_question" in c:
        q = c["community_only_question"]
        comm = map_community(t, c)
        bad = [not is_blank(r.get(q["column"])) and text(r.get(q["column"])) != q["not_applicable"]
               and k is not None and k != q["community"] for r, k in zip(rows, comm)]
        out += _f(t, c, bad, "W07", "WARN", q["column"],
                  "question for %s answered by another community" % q["community"])
    if "id_columns" in c:
        out += _f(t, c, duplicate_content_mask(t, c["id_columns"]), "W09", "WARN", "",
                  "row identical to another row except ids")
    return out
