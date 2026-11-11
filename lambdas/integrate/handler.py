"""Integrate step: trusted Happy Home rows -> the household analysis table for Q1-Q3 (T13 risk score).

Writes curated/_pipeline/staging/<batch_id>/happy_home_household.parquet; Verify checks it and only
then publishes it to curated/happy_home_household/. The two surveys are not joined per household
(different years, areas and income bands), so SoVI is compared at group level later (#24).
Columns: contracts/curated_happy_home_household.json.
"""
from common import lake, parquet

TABLE = "happy_home_household"
BURDEN_SCORE = {"high": 1.0, "possibly_high": 0.5, "low": 0.0}


def risk(row, burden_weight):
    """T13 (D7): heat/13 + housing/5 + w x burden_score + coping/6. None unless usable for Q3 with every part."""
    parts = (row["heat_impact_score"], row["housing_heat_score"], row["burden_class"], row["coping_limit_score"])
    if not row["usable_q3"] or any(p is None for p in parts):
        return None
    heat, housing, burden, coping = parts
    return round(heat / 13 + housing / 5 + burden_weight * BURDEN_SCORE[burden] + coping / 6, 6)


def ranks(scores):
    """1 = highest score; equal scores share a rank (1, 2, 2, 4). None stays None."""
    ordered = sorted((s for s in scores if s is not None), reverse=True)
    first = {}
    for i, s in enumerate(ordered, start=1):
        first.setdefault(s, i)
    return [first[s] if s is not None else None for s in scores]


def curated_rows(trusted, schema):
    names = [c["name"] for c in schema["columns"]]
    out = []
    for t in trusted:
        row = {n: t[n] for n in names if n in t}
        row["burden_score"] = BURDEN_SCORE.get(t["burden_class"]) if t["burden_class"] else None
        row["risk_score"] = risk(t, 2)
        row["risk_score_equal"] = risk(t, 1)
        out.append(row)
    for col, rank_col in (("risk_score", "risk_rank"), ("risk_score_equal", "risk_rank_equal")):
        for row, r in zip(out, ranks([row[col] for row in out])):
            row[rank_col] = r
    return out


def run(batch_id):
    if lake.source_of(batch_id) != "happy_home":
        raise ValueError("no integrate step for source %r" % lake.source_of(batch_id))
    trusted = parquet.read(lake.get_bytes(lake.trusted_key(batch_id))).to_pylist()
    schema = lake.contract("curated_happy_home_household")
    rows = curated_rows(trusted, schema)
    key = lake.staging_key(batch_id, TABLE)
    lake.put_bytes(key, parquet.to_bytes(rows, schema))
    return key, len(rows)


def handler(event, context):
    lake.force_fail(event, "integrate")
    key, n = run(event["batch_id"])
    return {**event, "curated_staging_key": key, "curated_rows": n}
