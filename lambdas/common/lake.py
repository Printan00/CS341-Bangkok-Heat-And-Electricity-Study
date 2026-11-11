"""S3 data-lake helpers shared by the pipeline Lambdas.

Layout for one batch (batch_id = <source>-<sha256[:12]>, written by scripts/ingest.py):
  raw/<source>/<batch_id>/<file>.xlsx                       original file (read-only for Lambdas)
  quarantine/<source>/<batch_id>/                           Validate: report, violations, quarantined rows, manifest
  trusted/<source>/batch_id=<batch_id>/part-0.parquet       Transform: checked rows, no coordinates/names
  curated/_pipeline/staging/<batch_id>/<table>.parquet      Integrate: analysis table waiting for Verify
  curated/<table>/part-0.parquet                            Verify: published table (latest batch replaces old)
  curated/_pipeline/success/<batch_id>/_SUCCESS.json        Verify: written only when every check passes
"""
import json
import os
from pathlib import Path

CONTRACTS = Path(__file__).resolve().parent / "contracts"
_client = None


def contract(name):
    return json.loads((CONTRACTS / ("%s.json" % name)).read_text(encoding="utf-8"))


def s3():
    global _client
    if _client is None:
        import boto3  # in the Lambda runtime; imported lazily so tests can run without it

        _client = boto3.client("s3")
    return _client


def bucket():
    return os.environ["LAKE_BUCKET"]


def source_of(batch_id):
    return batch_id.rsplit("-", 1)[0]


def get_bytes(key):
    return s3().get_object(Bucket=bucket(), Key=key)["Body"].read()


def get_json(key):
    return json.loads(get_bytes(key))


def put_bytes(key, body, content_type="application/octet-stream"):
    s3().put_object(Bucket=bucket(), Key=key, Body=body, ContentType=content_type)


def put_json(key, obj):
    put_bytes(key, json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8"), "application/json")


def list_keys(prefix):
    keys, token = [], None
    while True:
        kw = {"Bucket": bucket(), "Prefix": prefix}
        if token:
            kw["ContinuationToken"] = token
        page = s3().list_objects_v2(**kw)
        keys += [o["Key"] for o in page.get("Contents", [])]
        token = page.get("NextContinuationToken")
        if not token:
            return keys


def raw_file(batch_id):
    """The one .xlsx of a batch under raw/<source>/<batch_id>/ (ingest writes exactly one)."""
    prefix = "raw/%s/%s/" % (source_of(batch_id), batch_id)
    files = [k for k in list_keys(prefix) if k.lower().endswith(".xlsx")]
    if not files:
        raise FileNotFoundError("no .xlsx under s3://%s/%s (run scripts/ingest.py first)" % (bucket(), prefix))
    if len(files) > 1:
        raise ValueError("expected one .xlsx under %s, found %d" % (prefix, len(files)))
    return files[0]


def quarantine_prefix(batch_id):
    return "quarantine/%s/%s/" % (source_of(batch_id), batch_id)


def trusted_key(batch_id):
    return "trusted/%s/batch_id=%s/part-0.parquet" % (source_of(batch_id), batch_id)


def staging_key(batch_id, table):
    return "curated/_pipeline/staging/%s/%s.parquet" % (batch_id, table)


def curated_key(table):
    return "curated/%s/part-0.parquet" % table


def success_key(batch_id):
    return "curated/_pipeline/success/%s/_SUCCESS.json" % batch_id


def force_fail(event, step):
    """Smoke-test hook: {"fail_at": "<step>"} in the execution input makes that step fail."""
    if event.get("fail_at") == step:
        raise RuntimeError("forced failure for testing")
