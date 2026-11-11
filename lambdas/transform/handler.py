"""Transform step (#20): passed rows of a validated batch -> trusted/<source>/batch_id=<id>/part-0.parquet.

Reads the raw file again plus Validate's manifest.json, and only proceeds when the manifest
status is "passed". Columns follow contracts/trusted_happy_home.json exactly (an allowlist):
no coordinates, community name text or interviewer code. A rerun overwrites the same key.
"""
from common import lake, parquet
from common.xlsx import read_workbook
from transform.build import trusted_rows

SCHEMAS = {"happy_home": ("happy_home", "trusted_happy_home")}  # source -> (rules contract, schema contract)


def run(batch_id):
    source = lake.source_of(batch_id)
    if source not in SCHEMAS:
        raise ValueError("no transform for source %r" % source)
    manifest = lake.get_json(lake.quarantine_prefix(batch_id) + "manifest.json")
    if manifest.get("status") != "passed":
        raise ValueError("batch %s did not pass Validate (status=%s)" % (batch_id, manifest.get("status")))
    rules, schema = (lake.contract(n) for n in SCHEMAS[source])
    sheet = read_workbook(lake.get_bytes(manifest["raw_key"]))[rules["data_sheet"]]
    rows = trusted_rows(sheet, manifest, rules)
    key = lake.trusted_key(batch_id)
    lake.put_bytes(key, parquet.to_bytes(rows, schema))
    return key, len(rows)


def handler(event, context):
    lake.force_fail(event, "transform")
    key, n = run(event["batch_id"])
    return {**event, "trusted_key": key, "trusted_rows": n}
