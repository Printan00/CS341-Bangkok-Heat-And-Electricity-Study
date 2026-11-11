"""Shared pieces for the validate step: tables, violations, row split, batch checks, report.

Rules are specified in reports/validation_rules.md. Standard library only.
"""
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

K_MIN = 5  # counts below this are shown as "<5" in reports
CONTRACT_DIR = Path(__file__).parent / "contracts"


@dataclass
class Table:
    header: list
    rows: list  # one dict per record, keyed by header name

    def column(self, name):
        return [r.get(name) for r in self.rows]


@dataclass
class Violation:
    rule_id: str
    severity: str        # FAIL | WARN | INFO
    row_index: object    # position in Table.rows, None for batch-level
    record_id: object
    source_row: object   # Excel row number (header = row 1), None for batch-level
    column: str
    message: str

    def to_dict(self):
        return asdict(self)


def batch_violation(rule_id, severity, message):
    return Violation(rule_id, severity, None, None, None, "", message)


def load_contract(name):
    with open(CONTRACT_DIR / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


# ---------- value helpers ----------

def is_blank(v):
    return v is None or (isinstance(v, float) and v != v) or (isinstance(v, str) and v.strip() == "")


def text(v):
    return "" if is_blank(v) else str(v).strip()


def norm_label(v):
    """Compare labels ignoring whitespace and hyphen/en-dash differences."""
    return re.sub(r"\s+", "", str(v)).replace("-", "–")


def to_number(v):
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def flag_on(v):
    return to_number(v) == 1


# ---------- violations and row split ----------

def flag(table, mask, rule_id, severity, column, message, id_col):
    out = []
    for i, bad in enumerate(mask):
        if bad:
            rid = table.rows[i].get(id_col)
            out.append(Violation(rule_id, severity, i, None if is_blank(rid) else rid, i + 2, column, message))
    return out


def duplicate_content_mask(table, id_columns):
    keys = [tuple(str(r.get(h)) for h in table.header if h not in id_columns) for r in table.rows]
    counts = {}
    for k in keys:
        counts[k] = counts.get(k, 0) + 1
    return [counts[k] > 1 for k in keys]


def finalize(table, violations):
    """Any FAIL -> quarantine (with rule_ids); WARN rule ids -> dq_flags on passed rows."""
    fail, warn = {}, {}
    for v in violations:
        if v.row_index is None or v.severity not in ("FAIL", "WARN"):
            continue
        ids = (fail if v.severity == "FAIL" else warn).setdefault(v.row_index, [])
        if v.rule_id not in ids:
            ids.append(v.rule_id)
    passed, quarantine = [], []
    for i, r in enumerate(table.rows):
        if i in fail:
            quarantine.append({**r, "rule_ids": ";".join(fail[i])})
        else:
            passed.append({**r, "dq_flags": ";".join(warn.get(i, []))})
    return passed, quarantine


def suppress(n):
    return "<%d" % K_MIN if 0 < n < K_MIN else str(n)


def quarantine_rate_violation(n_quarantined, n_rows, max_rate):
    if n_rows and n_quarantined / n_rows > max_rate:
        return batch_violation("B06", "FAIL", "quarantined %s of %d rows (> %.0f%%)"
                               % (suppress(n_quarantined), n_rows, max_rate * 100))
    return None


# ---------- batch ----------

@dataclass
class BatchResult:
    source: str
    batch_id: str
    sha256: str
    status: str                # passed | failed
    batch_violations: list
    row_violations: list
    passed: object = None      # list of row dicts, None when the batch stopped before row checks
    quarantine: object = None

    def report(self):
        """Aggregate-only summary: no ids, no raw values; per-rule counts use <5."""
        checked = self.passed is not None
        per_rule = {}
        for v in self.row_violations:
            per_rule.setdefault(v.rule_id, {"severity": v.severity, "rows": set()})["rows"].add(v.row_index)
        return {
            "source": self.source,
            "batch_id": self.batch_id,
            "source_sha256": self.sha256,
            "status": self.status,
            "rows_in": len(self.passed) + len(self.quarantine) if checked else None,
            "rows_passed": len(self.passed) if checked else None,
            "rows_quarantined": len(self.quarantine) if checked else None,
            "rows_with_warnings": sum(1 for r in self.passed if r["dq_flags"]) if checked else None,
            "batch_rules": [{"rule_id": v.rule_id, "severity": v.severity, "message": v.message}
                            for v in self.batch_violations],
            "row_rules": {k: {"severity": d["severity"], "rows": suppress(len(d["rows"]))}
                          for k, d in sorted(per_rule.items())},
        }


def structure_checks(sheets, c):
    """B01 privacy first, then B02 sheets, B03 schema, B04 row count."""
    out = []
    data = sheets.get(c["data_sheet"])
    header = data.header if data is not None else []
    leaked = [col for col in c.get("forbidden_columns", []) if col in header]
    if leaked:
        out.append(batch_violation("B01", "FAIL", "forbidden column(s) present: %s" % ", ".join(leaked)))
    settings = sheets.get(c.get("settings_sheet"))
    if settings is not None:
        key_col, val_col = settings.header[0], settings.header[1]
        values = {str(r[key_col]): r[val_col] for r in settings.rows}
        for key, rule in c.get("settings_rules", {}).items():
            v = values.get(key)
            ok = v is not None and ("eq" not in rule or v == rule["eq"]) \
                and ("max" not in rule or (to_number(v) is not None and to_number(v) <= rule["max"]))
            if not ok:
                out.append(batch_violation("B01", "FAIL", "anonymisation setting %s not as contracted" % key))
    missing = [s for s in c["required_sheets"] if s not in sheets]
    if missing:
        out.append(batch_violation("B02", "FAIL", "missing sheet(s): %s" % ", ".join(missing)))
    if data is not None and header != c["columns"]:
        out.append(batch_violation("B03", "FAIL", "header differs from contract (%d vs %d columns)"
                                   % (len(header), len(c["columns"]))))
    if data is not None:
        if not data.rows:
            out.append(batch_violation("B04", "FAIL", "data sheet has no rows"))
        elif c.get("expected_rows") and len(data.rows) != c["expected_rows"]:
            out.append(batch_violation("B04", "WARN", "%d rows, expected %d" % (len(data.rows), c["expected_rows"])))
    return out


def run_batch(source, data, c, row_checks, enrich, batch_id=None):
    from xlsx import read_workbook  # local import: xlsx imports Table from this module

    sha = hashlib.sha256(data).hexdigest()
    batch_id = batch_id or sha[:12]
    sheets = read_workbook(data)
    batch = structure_checks(sheets, c)
    if any(v.severity == "FAIL" for v in batch):
        return BatchResult(source, batch_id, sha, "failed", batch, [])
    table = sheets[c["data_sheet"]]
    rows = row_checks(table, c)
    passed, quarantine = finalize(enrich(table, c), rows)
    rate = quarantine_rate_violation(len(quarantine), len(table.rows), c.get("max_quarantine_rate", 0.10))
    if rate:
        batch.append(rate)
    status = "failed" if any(v.severity == "FAIL" for v in batch) else "passed"
    return BatchResult(source, batch_id, sha, status, batch, rows, passed, quarantine)
