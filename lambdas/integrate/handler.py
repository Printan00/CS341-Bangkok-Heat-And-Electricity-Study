"""Integrate step: trusted Happy Home rows -> two curated tables.

1. happy_home_household: the household analysis table for Q1-Q3 (T13 risk score, weights D7).
   Columns: contracts/curated_happy_home_household.json.
2. happy_home_risk: the five-group risk score (reports/risk_score_formulas.md), formulas in scoring.py.
   Columns: contracts/curated_happy_home_risk.json. Added next to the T13 columns, which stay until the
   team decides whether to drop them.

Both go to curated/_pipeline/staging/<batch_id>/<table>.parquet; Verify checks them and only then
publishes them to curated/<table>/. The two surveys are not joined per household
(different years, areas and income bands), so SoVI is compared at group level later (#24).

LST (reports/gee_lst_pipeline.md):
- a gee_lst batch stages community_dim (one row per community, with lst_score) for its own Verify;
  a gee_lst_household batch stages household_lst (one row per household) the same way.
- a happy_home batch joins the PUBLISHED curated/community_dim/ (on community_key) and curated/household_lst/
  (on household_code) into happy_home_risk. A table not published yet -> its LST columns are null.
  So: run the gee batches first; after a new gee batch, rerun Happy Home with "force": true.
"""
from common import lake, parquet
from common.gee import SOURCES as GEE_SOURCES
from integrate.scoring import lst_score, ranks, risk_rows

TABLE = "happy_home_household"
RISK_TABLE = "happy_home_risk"
BURDEN_SCORE = {"high": 1.0, "possibly_high": 0.5, "low": 0.0}


def risk(row, burden_weight):
    """T13 (D7): heat/13 + housing/5 + w x burden_score + coping/6. None unless usable for Q3 with every part."""
    parts = (row["heat_impact_score"], row["housing_heat_score"], row["burden_class"], row["coping_limit_score"])
    if not row["usable_q3"] or any(p is None for p in parts):
        return None
    heat, housing, burden, coping = parts
    return round(heat / 13 + housing / 5 + burden_weight * BURDEN_SCORE[burden] + coping / 6, 6)


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


def lst_table_rows(trusted, score_range, schema):
    names = [c["name"] for c in schema["columns"]]
    return [{n: {**t, "lst_score": lst_score(t["lst_mean_c"], score_range)}[n] for n in names} for t in trusted]


def published_lst(source):
    """key -> row of the published table of a gee source ({} before its first batch)."""
    cfg = GEE_SOURCES[source]
    key = lake.curated_key(cfg["table"])
    if key not in lake.list_keys(key):
        return {}
    return {r[cfg["out_key"]]: r for r in parquet.read(lake.get_bytes(key)).to_pylist()}


def run_gee(batch_id):
    cfg = GEE_SOURCES[lake.source_of(batch_id)]
    trusted = parquet.read(lake.get_bytes(lake.trusted_key(batch_id))).to_pylist()
    schema = lake.contract(cfg["curated"])
    rows = lst_table_rows(trusted, lake.contract("gee_lst")["lst_score_c"], schema)
    key = lake.staging_key(batch_id, cfg["table"])
    lake.put_bytes(key, parquet.to_bytes(rows, schema))
    return key, len(rows)


def run(batch_id):
    if lake.source_of(batch_id) in GEE_SOURCES:
        return run_gee(batch_id)
    if lake.source_of(batch_id) != "happy_home":
        raise ValueError("no integrate step for source %r" % lake.source_of(batch_id))
    trusted = parquet.read(lake.get_bytes(lake.trusted_key(batch_id))).to_pylist()
    schema = lake.contract("curated_happy_home_household")
    rows = curated_rows(trusted, schema)
    key = lake.staging_key(batch_id, TABLE)
    lake.put_bytes(key, parquet.to_bytes(rows, schema))
    risk_schema = lake.contract("curated_happy_home_risk")
    income_bands = [b[0] for b in lake.contract("happy_home")["income_bands"]]
    lake.put_bytes(lake.staging_key(batch_id, RISK_TABLE),
                   parquet.to_bytes(risk_rows(trusted, income_bands, risk_schema, published_lst("gee_lst"),
                                              published_lst("gee_lst_household")), risk_schema))
    return key, len(rows)


def handler(event, context):
    lake.force_fail(event, "integrate")
    key, n = run(event["batch_id"])
    if lake.source_of(event["batch_id"]) in GEE_SOURCES:
        return {**event, "curated_staging_key": key, "curated_rows": n}
    return {**event, "curated_staging_key": key, "risk_staging_key": lake.staging_key(event["batch_id"], RISK_TABLE),
            "curated_rows": n}
