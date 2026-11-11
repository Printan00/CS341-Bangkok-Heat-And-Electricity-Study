data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
}

# Data lake: raw/ quarantine/ trusted/ curated/ prefixes (created by the pipeline on first write)
resource "aws_s3_bucket" "lake" {
  bucket = "${var.project}-lake-${local.account_id}"
}

# Versioning so raw arrivals are never lost to an overwrite
resource "aws_s3_bucket_versioning" "lake" {
  bucket = aws_s3_bucket.lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "athena_results" {
  bucket = "${var.project}-athena-results-${local.account_id}"
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket                  = aws_s3_bucket.athena_results.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Empty "folder" markers so the zones are visible in the S3 console before any data arrives
resource "aws_s3_object" "lake_zones" {
  for_each = toset(["raw", "quarantine", "trusted", "curated"])
  bucket   = aws_s3_bucket.lake.id
  key      = "${each.key}/"
  content  = ""
}
