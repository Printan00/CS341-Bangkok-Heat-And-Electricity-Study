# Least-privilege roles for the pipeline. Names use "${var.project}-*" patterns
# because the Lambda functions, workgroup and Glue database are created in #17.

locals {
  lake_arn = aws_s3_bucket.lake.arn
}

# ---------- Lambda (all pipeline steps share one role) ----------
data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.project}-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "lambda_s3" {
  statement {
    actions   = ["s3:ListBucket"]
    resources = [local.lake_arn]
  }
  # Raw is read-only for the pipeline: only ingest (#18) writes there
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${local.lake_arn}/raw/*"]
  }
  statement {
    actions = ["s3:GetObject", "s3:PutObject"]
    resources = [
      "${local.lake_arn}/quarantine/*",
      "${local.lake_arn}/trusted/*",
      "${local.lake_arn}/curated/*",
    ]
  }
}

resource "aws_iam_role_policy" "lambda_s3" {
  name   = "lake-access"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_s3.json
}

# ---------- Step Functions ----------
data "aws_iam_policy_document" "sfn_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sfn" {
  name               = "${var.project}-sfn"
  assume_role_policy = data.aws_iam_policy_document.sfn_trust.json
}

data "aws_iam_policy_document" "sfn_invoke" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    resources = ["arn:aws:lambda:${var.region}:${local.account_id}:function:${var.project}-*"]
  }
}

resource "aws_iam_role_policy" "sfn_invoke" {
  name   = "invoke-pipeline-lambdas"
  role   = aws_iam_role.sfn.id
  policy = data.aws_iam_policy_document.sfn_invoke.json
}

# ---------- Glue Crawler (reads curated/ only) ----------
data "aws_iam_policy_document" "glue_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue_crawler" {
  name               = "${var.project}-glue-crawler"
  assume_role_policy = data.aws_iam_policy_document.glue_trust.json
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_crawler.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

data "aws_iam_policy_document" "glue_s3" {
  statement {
    actions   = ["s3:ListBucket"]
    resources = [local.lake_arn]
  }
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${local.lake_arn}/curated/*"]
  }
}

resource "aws_iam_role_policy" "glue_s3" {
  name   = "read-curated"
  role   = aws_iam_role.glue_crawler.id
  policy = data.aws_iam_policy_document.glue_s3.json
}

# ---------- Athena (no service role: Athena runs as the caller, so this is a policy to attach) ----------
data "aws_iam_policy_document" "athena_query" {
  statement {
    actions = [
      "athena:StartQueryExecution",
      "athena:StopQueryExecution",
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:GetWorkGroup",
    ]
    resources = ["arn:aws:athena:${var.region}:${local.account_id}:workgroup/${var.project}-*"]
  }
  statement {
    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetTable",
      "glue:GetTables",
      "glue:GetPartition",
      "glue:GetPartitions",
    ]
    resources = [
      "arn:aws:glue:${var.region}:${local.account_id}:catalog",
      "arn:aws:glue:${var.region}:${local.account_id}:database/${var.project}*",
      "arn:aws:glue:${var.region}:${local.account_id}:table/${var.project}*/*",
    ]
  }
  statement {
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [local.lake_arn, aws_s3_bucket.athena_results.arn]
  }
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${local.lake_arn}/curated/*"]
  }
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"]
    resources = ["${aws_s3_bucket.athena_results.arn}/*"]
  }
}

resource "aws_iam_policy" "athena_query" {
  name        = "${var.project}-athena-query"
  description = "Query curated tables through Athena; attach to users or QuickSight"
  policy      = data.aws_iam_policy_document.athena_query.json
}
