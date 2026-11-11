import io
import os
import sys
from pathlib import Path

import pytest

# All Lambdas are deployed from the one folder lambdas/ (infra/terraform/lambda.tf), so tests import
# them the same way: common.*, validate.*, transform.*, integrate.*, verify.*
LAMBDAS = Path(__file__).resolve().parents[1] / "lambdas"
sys.path.insert(0, str(LAMBDAS))

from common import lake  # noqa: E402

SAMPLE_DIR = os.environ.get("BHES_SAMPLE_DIR")
HH_FILE = "ThaiCI_Household_Questionaire_anonymized.xlsx"


class FakeS3:
    """The few S3 calls the Lambdas make, kept in a dict."""

    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType=None, **kw):
        self.objects[Key] = Body if isinstance(Body, bytes) else Body.encode()

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise KeyError("NoSuchKey: %s" % Key)
        return {"Body": io.BytesIO(self.objects[Key])}

    def list_objects_v2(self, Bucket, Prefix, **kw):
        return {"Contents": [{"Key": k} for k in sorted(self.objects) if k.startswith(Prefix)]}


@pytest.fixture
def s3(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(lake, "_client", fake)
    monkeypatch.setenv("LAKE_BUCKET", "test-lake")
    return fake


@pytest.fixture(scope="session")
def contract():
    return lake.contract("happy_home")


@pytest.fixture(scope="session")
def real_hh_bytes():
    if not SAMPLE_DIR:
        pytest.skip("set BHES_SAMPLE_DIR to the folder with the real survey files (never committed)")
    path = Path(SAMPLE_DIR) / HH_FILE
    if not path.exists():
        pytest.skip("%s not found in BHES_SAMPLE_DIR" % HH_FILE)
    return path.read_bytes()
