# One function per pipeline step. Code lives in lambdas/<step>/handler.py; editing it and
# running `terraform apply` redeploys that function.
locals {
  steps = ["check_batch", "validate", "transform", "integrate", "verify"]
}

data "archive_file" "step" {
  for_each    = toset(local.steps)
  type        = "zip"
  source_dir  = "${path.module}/../../lambdas/${each.key}"
  output_path = "${path.module}/.build/${each.key}.zip"
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
  handler          = "handler.handler"
  filename         = data.archive_file.step[each.key].output_path
  source_code_hash = data.archive_file.step[each.key].output_base64sha256
  timeout          = 60
  memory_size      = 512

  environment {
    variables = {
      LAKE_BUCKET = aws_s3_bucket.lake.bucket
    }
  }

  depends_on = [aws_cloudwatch_log_group.step]
}
