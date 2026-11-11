"""Parquet in/out with the column types fixed by a schema contract (contracts/trusted_*.json, curated_*.json).

pyarrow comes from the AWS SDK for pandas Lambda layer (infra/terraform/lambda.tf); Validate does not use it.
"""
import io


def _pa():
    import pyarrow as pa
    import pyarrow.parquet as pq

    return pa, pq


def schema(contract):
    pa, _ = _pa()
    types = {"string": pa.string(), "int8": pa.int8(), "int32": pa.int32(),
             "float64": pa.float64(), "bool": pa.bool_()}
    return pa.schema([pa.field(c["name"], types[c["type"]], nullable=c["nullable"]) for c in contract["columns"]])


def to_bytes(records, contract):
    """records: list of dicts with exactly the contract's columns -> Parquet bytes."""
    pa, pq = _pa()
    names = [c["name"] for c in contract["columns"]]
    for r in records:
        if set(r) != set(names):
            extra, missing = sorted(set(r) - set(names)), sorted(set(names) - set(r))
            raise ValueError("record does not match the schema contract: extra %s, missing %s" % (extra, missing))
    table = pa.Table.from_pylist(records, schema=schema(contract))
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    return buf.getvalue()


def read(data):
    """Parquet bytes -> pyarrow Table."""
    _, pq = _pa()
    return pq.read_table(io.BytesIO(data))
