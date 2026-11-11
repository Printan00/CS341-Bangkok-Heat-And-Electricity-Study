# One function per pipeline step. Code lives in lambdas/<step>/handler.py and shared code in
# lambdas/common/, so every function gets the same zip of lambdas/ and its own handler.
# Editing any of it and running `terraform apply` redeploys the functions.
locals {
  steps = ["check_batch", "validate", "transform", "integrate", "verify"]
  # Steps that read/write Parquet need pyarrow, from the AWS SDK for pandas layer
  parquet_steps = ["transform", "integrate", "verify"]
}

data "archive_file" "lambdas" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambdas"
  output_path = "${path.module}/.build/lambdas.zip"
  excludes    = ["**/__pycache__/**", "**/*.pyc", "**/.DS_Store"]
}

resource "aws_cloudwatch_log_group" "step" {
  for_each          = toset(local.steps)
  name              = "/aws/lambda/${var.project}-${replace(each.key, "_", "-")}"
  retention_in_days = 14
}

resource "aws_lambda_function" "step" {
  for_each         = toset(local.steps)
  function_name    = "${var.project}-${replace(each.key, "_", "-")}"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.13"
  handler          = "${each.key}.handler.handler"
  filename         = data.archive_file.lambdas.output_path
  source_code_hash = data.archive_file.lambdas.output_base64sha256
  layers           = contains(local.parquet_steps, each.key) ? [var.pandas_layer_arn] : []
  timeout          = 60
  memory_size      = 512

  environment {
    variables = {
      LAKE_BUCKET = aws_s3_bucket.lake.bucket
    }
  }

  depends_on = [aws_cloudwatch_log_group.step]
}
