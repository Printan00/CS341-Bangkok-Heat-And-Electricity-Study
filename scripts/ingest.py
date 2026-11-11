#!/usr/bin/env python3
"""Upload the survey xlsx files from local data/ into the S3 Raw zone.

Each file goes to incoming/ first, then is copied to raw/<source>/<batch_id>/ with
metadata (batch_id, source, ingested_at, sha256), plus a _manifest.json ingest log.
batch_id = <source>-<sha256[:12]>: the same file always gets the same batch_id, so
a rerun skips it instead of creating a duplicate. Nothing in raw/ is ever overwritten.

Usage:
    python scripts/ingest.py --bucket <lake bucket> [--data-dir data] [--region ap-southeast-1]
Requires: boto3 (see scripts/requirements.txt)
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from profile_codebook import HH_FILE, SOVI_FILE

SOURCES = {"happy_home": Path(HH_FILE).name, "sovi": Path(SOVI_FILE).name}


def exists(s3, bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise


def ingest(s3, bucket, source, path):
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    batch_id = f"{source}-{sha[:12]}"
    raw_key = f"raw/{source}/{batch_id}/{path.name}"
    if exists(s3, bucket, raw_key):
        return batch_id, sha, "SKIP (already ingested)"

    ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta = {"batch_id": batch_id, "source": source, "ingested_at": ingested_at, "sha256": sha}
    incoming_key = f"incoming/{batch_id}/{path.name}"
    put = s3.put_object(Bucket=bucket, Key=incoming_key, Body=data,
                        ChecksumAlgorithm="SHA256", Metadata=meta)
    s3.copy_object(Bucket=bucket, Key=raw_key, MetadataDirective="COPY",
                   CopySource={"Bucket": bucket, "Key": incoming_key, "VersionId": put["VersionId"]})
    # Delete by version id: the bucket is versioned, a plain delete would keep a hidden copy
    s3.delete_object(Bucket=bucket, Key=incoming_key, VersionId=put["VersionId"])

    manifest = {**meta, "files": [{"name": path.name, "sha256": sha, "bytes": len(data)}]}
    s3.put_object(Bucket=bucket, Key=f"raw/{source}/{batch_id}/_manifest.json",
                  Body=json.dumps(manifest, indent=2).encode(), ContentType="application/json")
    return batch_id, sha, "INGESTED"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--data-dir", default="data", type=Path)
    ap.add_argument("--region", default="ap-southeast-1")
    args = ap.parse_args()

    files = {}
    for source, name in SOURCES.items():
        found = sorted(args.data_dir.rglob(name))
        if not found:
            sys.exit(f"missing {name} under {args.data_dir}/")
        files[source] = found[0]

    s3 = boto3.client("s3", region_name=args.region)
    print(f"{'batch_id':<26} {'files':>5}  {'sha256':<64}  status")
    for source, path in files.items():
        batch_id, sha, status = ingest(s3, args.bucket, source, path)
        print(f"{batch_id:<26} {1:>5}  {sha}  {status}")


if __name__ == "__main__":
    main()
