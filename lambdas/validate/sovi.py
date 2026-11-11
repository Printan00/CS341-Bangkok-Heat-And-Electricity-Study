"""SoVI V8 rules. See reports/validation_rules.md §4.2 and §5."""
import re

from core import Table, duplicate_content_mask, flag, is_blank, load_contract, norm_label, run_batch, text, to_number

SOURCE = "sovi"


def validate(data, contract=None, batch_id=None):
    return run_batch(SOURCE, data, contract or load_contract(SOURCE), row_checks, enrich, batch_id)


def row_checks(t, c):
    out = []
    if "id_column" in c:
        out += check_id(t, c)
    if "community_map" in c:
        out += check_community(t, c)
    if "allowed_values" in c:
        out += check_domain(t, c)
    if "gate_counts" in c:
        out += check_gate_counts(t, c)
    if "household_size" in c:
        out += check_household_size(t, c)
    if "score_pattern" in c:
        out += check_scores(t, c)
    return out + check_warnings(t, c)


def _f(t, c, mask, rule, sev, col, msg):
    return flag(t, mask, rule, sev, col, msg, id_col=c["id_column"])


def _count(v):
    """Member counts: '-' or blank means none."""
    return 0.0 if is_blank(v) or text(v) == "-" else to_number(v)


def check_id(t, c):
    ids = t.column(c["id_column"])
    present = [v for v in ids if not is_blank(v)]
    bad = [is_blank(v) or not re.match(c["id_pattern"], str(v)) or present.count(v) > 1 for v in ids]
    return _f(t, c, bad, "S01", "FAIL", c["id_column"], "respondent id blank, wrong format or duplicated")


def map_community(t, c):
    table = {k.strip(): v for k, v in c["community_map"].items()}
    return [None if is_blank(v) else table.get(str(v).strip()) for v in t.column(c["community_column"])]


def check_community(t, c):
    return _f(t, c, [k is None for k in map_community(t, c)], "S02", "FAIL", c["community_column"],
              "community not in the list of surveyed communities")


def enrich(t, c):
    if "community_map" not in c:
        return t
    keys = map_community(t, c)
    codes = []
    for v in t.column(c["community_column"]):
        m = re.match(r"^\((\d+)\)", text(v))
        codes.append(m.group(1) if m else None)
    return Table(t.header + ["community_key", "community_code"],
                 [{**r, "community_key": k, "community_code": code} for r, k, code in zip(t.rows, keys, codes)])


def check_domain(t, c):
    out = []
    for col, allowed in c["allowed_values"].items():
        ok = {norm_label(a) for a in allowed}
        out += _f(t, c, [not is_blank(v) and norm_label(v) not in ok for v in t.column(col)],
                  "S03", "FAIL", col, "value not in questionnaire options")
    return out


def check_gate_counts(t, c):
    out = []
    for g in c["gate_counts"]:
        bad = []
        for r in t.rows:
            none, n = text(r.get(g["gate"])) == g["none_value"], _count(r.get(g["count"]))
            bad.append(n is None or (none and n > 0) or (not none and n == 0))
        out += _f(t, c, bad, "S04", "FAIL", g["count"], "yes/no answer disagrees with the count")
    return out


def check_household_size(t, c):
    h = c["household_size"]
    bands = {norm_label(k): v for k, v in h["bands"].items()}

    def bad(r):
        lo_hi = bands.get(norm_label(r.get(h["column"])))
        parts = [_count(r.get(col)) for col in h["totals"]]
        return lo_hi is None or None in parts or not (lo_hi[0] <= sum(parts) <= lo_hi[1])

    return _f(t, c, [bad(r) for r in t.rows], "S05", "FAIL", h["column"],
              "household size band disagrees with member totals")


def check_scores(t, c):
    out = []
    for col in t.header:
        if not re.match(c["score_pattern"], col):
            continue
        rng = c.get("score_exceptions", {}).get(col)
        bad = []
        for v in t.column(col):
            n = to_number(v)
            if is_blank(v):
                bad.append(False)
            elif n is None:
                bad.append(True)
            else:
                bad.append(not (rng[0] <= n <= rng[1]) if rng else n not in c["score_allowed"])
        out += _f(t, c, bad, "S06", "FAIL", col, "score outside the scoring key")
    return out


def check_warnings(t, c):
    out = []
    for s in c.get("member_sums", []):
        bad = [_count(r.get(s["total"])) != sum(_count(r.get(p)) or 0 for p in s["parts"]) for r in t.rows]
        out += _f(t, c, bad, "W08", "WARN", s["total"], "member total differs from the sum of its parts")
    if "id_columns" in c:
        out += _f(t, c, duplicate_content_mask(t, c["id_columns"]), "W09", "WARN", "",
                  "row identical to another row except ids")
    return out
