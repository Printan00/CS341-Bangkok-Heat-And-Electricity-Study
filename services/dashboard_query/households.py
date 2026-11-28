"""Read allowlisted household fields from the curated Happy Home Risk Parquet."""

import io
import os

import boto3
from pyarrow import parquet

Q3_COLUMNS = (
    "household_code", "heat_risk", "housing_risk", "finance_risk", "burden_risk",
    "coping_risk", "burden_min", "burden_max", "exposure", "vulnerability",
    "risk_score", "risk_rank", "risk_quadrant", "lst_mean_c", "lst_score",
    "lst_batch_id", "lst_hh_c", "lst_hh_score", "lst_hh_batch_id", "batch_id", "source_row",
)
Q2_COLUMNS = (
    "household_code", "income_group", "has_aircon", "burden_class", "burden_min", "burden_max",
    "burden_risk", "finance_risk", "coping_risk", "exposure", "vulnerability", "risk_score", "risk_rank",
)
S3 = boto3.client("s3")


def read_households(columns=Q3_COLUMNS):
    obj = S3.get_object(
        Bucket=os.environ["LAKE_BUCKET"],
        Key="curated/happy_home_risk/part-0.parquet",
    )
    with obj["Body"] as body:
        source = io.BytesIO(body.read())
    source = parquet.ParquetFile(source)
    if not set(columns).issubset(source.schema_arrow.names):
        raise ValueError("Unexpected household schema")
    table = source.read(columns=list(columns))
    # Default to highest risk, with missing ranks last.
    rows = sorted(table.to_pylist(), key=lambda row: (
        row["risk_rank"] is None, row["risk_rank"] or 0, row.get("source_row", row["household_code"]),
    ))
    return {"columns": columns, "rows": rows}
