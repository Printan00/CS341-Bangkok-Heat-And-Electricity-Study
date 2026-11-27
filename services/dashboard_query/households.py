"""Read the fixed, internal Q3 Parquet export without writing query results to S3."""

import io
import os

import boto3
from pyarrow import parquet

COLUMNS = (
    "household_code", "heat_risk", "housing_risk", "finance_risk", "burden_risk",
    "coping_risk", "burden_min", "burden_max", "exposure", "vulnerability",
    "risk_score", "risk_rank", "risk_quadrant", "lst_mean_c", "lst_score",
    "lst_batch_id", "lst_hh_c", "lst_hh_score", "lst_hh_batch_id", "batch_id", "source_row",
)
S3 = boto3.client("s3")


def read_households():
    obj = S3.get_object(
        Bucket=os.environ["LAKE_BUCKET"],
        Key="curated/happy_home_risk/part-0.parquet",
    )
    with obj["Body"] as body:
        source = io.BytesIO(body.read())
    table = parquet.ParquetFile(source).read(columns=list(COLUMNS))
    # Default to highest risk, with missing ranks last.
    rows = sorted(table.to_pylist(), key=lambda row: (
        row["risk_rank"] is None, row["risk_rank"] or 0, row["source_row"],
    ))
    return {"columns": COLUMNS, "rows": rows}
