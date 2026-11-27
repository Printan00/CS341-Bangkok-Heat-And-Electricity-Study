"""Serve the published Happy Home Q3 group summary through API Gateway."""

import json
import logging
import os
import time
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

ATHENA = boto3.client("athena", config=Config(connect_timeout=2, read_timeout=3))
SQL = Path(__file__).with_name("q3.sql").read_text(encoding="utf-8")
GROUPS = {"help_first", "watch", "lower_exposure"}
METRICS = ("risk_score", "exposure", "vulnerability", "heat", "housing", "finance", "burden", "coping")
COLUMNS = ("priority_group", "suppressed", "households", *METRICS)
LOGGER = logging.getLogger(__name__)


def fetch_rows(query_id):
    # This fixed query can return at most three groups plus a header.
    result = ATHENA.get_query_results(QueryExecutionId=query_id, MaxResults=10)
    rows = result["ResultSet"]["Rows"]
    header = tuple(cell.get("VarCharValue") for cell in rows[0]["Data"])
    if header != COLUMNS or result.get("NextToken"):
        raise ValueError("Unexpected Athena result schema")

    summary = []
    seen = set()
    for row in rows[1:]:
        values = dict(zip(COLUMNS, (cell.get("VarCharValue") for cell in row["Data"]), strict=True))
        group = values["priority_group"]
        if group not in GROUPS or group in seen or values["suppressed"] not in {"true", "false"}:
            raise ValueError("Unexpected priority group")
        seen.add(group)
        suppressed = values["suppressed"] == "true"
        households = int(values["households"]) if values["households"] is not None else None
        if (suppressed and households is not None) or (not suppressed and (households is None or households < 5)):
            raise ValueError("Unexpected disclosure state")
        summary.append({
            "group": group,
            "suppressed": suppressed,
            "households": households,
            **{key: float(values[key]) if not suppressed and values[key] is not None else None for key in METRICS},
        })
    return summary


def response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"},
        "body": json.dumps(body, allow_nan=False),
    }


def handler(event, context):
    try:
        if event.get("routeKey") == "GET /dashboard/q3/households":
            from households import read_households

            return response(200, read_households())

        deadline = time.monotonic() + min(16, context.get_remaining_time_in_millis() / 1000 - 4)
        query_id = ATHENA.start_query_execution(
            QueryString=SQL,
            WorkGroup=os.environ["ATHENA_WORKGROUP"],
            QueryExecutionContext={"Database": os.environ["ATHENA_DATABASE"]},
            ResultReuseConfiguration={"ResultReuseByAgeConfiguration": {"Enabled": True, "MaxAgeInMinutes": 5}},
        )["QueryExecutionId"]

        while time.monotonic() < deadline:
            status = ATHENA.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]["Status"]["State"]
            if status == "SUCCEEDED":
                return response(200, {"scoreVersion": "D27/D28", "threshold": 0.5, "rows": fetch_rows(query_id)})
            if status in {"FAILED", "CANCELLED"}:
                LOGGER.warning("Q3 Athena query %s ended with %s", query_id, status)
                return response(502, {"error": "q3_query_failed"})
            time.sleep(0.35)

        ATHENA.stop_query_execution(QueryExecutionId=query_id)
        return response(504, {"error": "q3_query_timeout"})
    except (BotoCoreError, ClientError, ValueError, KeyError, IndexError) as exc:
        LOGGER.error("Q3 request failed: %s", type(exc).__name__)
        return response(502, {"error": "q3_unavailable"})
