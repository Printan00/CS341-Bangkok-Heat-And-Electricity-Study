data "archive_file" "dashboard_query" {
  type        = "zip"
  source_dir  = "${path.module}/../../services/dashboard_query"
  output_path = "${path.module}/.build/dashboard-query.zip"
  excludes    = ["__pycache__", ".DS_Store"]
}

resource "aws_iam_role" "dashboard_query" {
  name               = "${var.project}-dashboard-query"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

resource "aws_cloudwatch_log_group" "dashboard_query" {
  name              = "/aws/lambda/${var.project}-dashboard-query"
  retention_in_days = 14
}

data "aws_iam_policy_document" "dashboard_query" {
  statement {
    actions = [
      "athena:StartQueryExecution", "athena:GetQueryExecution",
      "athena:GetQueryResults", "athena:StopQueryExecution", "athena:GetWorkGroup"
    ]
    resources = [aws_athena_workgroup.bhes.arn]
  }

  statement {
    actions = ["glue:GetDatabase", "glue:GetTable", "glue:GetPartition", "glue:GetPartitions"]
    resources = [
      "arn:aws:glue:${var.region}:${local.account_id}:catalog",
      "arn:aws:glue:${var.region}:${local.account_id}:database/${aws_glue_catalog_database.bhes.name}",
      "arn:aws:glue:${var.region}:${local.account_id}:table/${aws_glue_catalog_database.bhes.name}/happy_home_risk",
      "arn:aws:glue:${var.region}:${local.account_id}:table/${aws_glue_catalog_database.bhes.name}/happy_home_household"
    ]
  }

  statement {
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.lake.arn, aws_s3_bucket.athena_results.arn]
  }

  statement {
    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.lake.arn}/curated/happy_home_risk/*",
      "${aws_s3_bucket.lake.arn}/curated/happy_home_household/*"
    ]
  }

  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"]
    resources = ["${aws_s3_bucket.athena_results.arn}/*"]
  }

  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.dashboard_query.arn}:*"]
  }
}

resource "aws_iam_role_policy" "dashboard_query" {
  name   = "athena-q3"
  role   = aws_iam_role.dashboard_query.name
  policy = data.aws_iam_policy_document.dashboard_query.json
}

resource "aws_lambda_function" "dashboard_query" {
  function_name    = "${var.project}-dashboard-query"
  role             = aws_iam_role.dashboard_query.arn
  runtime          = "python3.13"
  handler          = "handler.handler"
  filename         = data.archive_file.dashboard_query.output_path
  source_code_hash = data.archive_file.dashboard_query.output_base64sha256
  timeout          = 23
  memory_size      = 512
  layers           = [var.pandas_layer_arn]

  environment {
    variables = {
      LAKE_BUCKET      = aws_s3_bucket.lake.bucket
      ATHENA_WORKGROUP = aws_athena_workgroup.bhes.name
      ATHENA_DATABASE  = aws_glue_catalog_database.bhes.name
    }
  }

  depends_on = [aws_iam_role_policy.dashboard_query]
}

resource "aws_apigatewayv2_api" "dashboard" {
  name          = "${var.project}-dashboard"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "dashboard_q3" {
  api_id                 = aws_apigatewayv2_api.dashboard.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.dashboard_query.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 25000
}

resource "aws_apigatewayv2_route" "dashboard_q3" {
  api_id             = aws_apigatewayv2_api.dashboard.id
  route_key          = "GET /dashboard/q3"
  target             = "integrations/${aws_apigatewayv2_integration.dashboard_q3.id}"
  authorization_type = "AWS_IAM"
}

resource "aws_apigatewayv2_stage" "dashboard" {
  api_id      = aws_apigatewayv2_api.dashboard.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 10
    throttling_rate_limit  = 5
  }
}

resource "aws_lambda_permission" "dashboard_q3" {
  statement_id  = "AllowGatewayQ3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dashboard_query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.dashboard.execution_arn}/$default/GET/dashboard/q3"
}

output "dashboard_q3_api_url" {
  value = "${aws_apigatewayv2_api.dashboard.api_endpoint}/dashboard/q3"
}

output "dashboard_q3_invoke_arn" {
  value = "${aws_apigatewayv2_api.dashboard.execution_arn}/$default/GET/dashboard/q3"
}

resource "aws_apigatewayv2_route" "dashboard_q3_households" {
  api_id             = aws_apigatewayv2_api.dashboard.id
  route_key          = "GET /dashboard/q3/households"
  target             = "integrations/${aws_apigatewayv2_integration.dashboard_q3.id}"
  authorization_type = "AWS_IAM"
}

resource "aws_lambda_permission" "dashboard_q3_households" {
  statement_id  = "AllowGatewayQ3Households"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dashboard_query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.dashboard.execution_arn}/$default/GET/dashboard/q3/households"
}

output "dashboard_q3_households_invoke_arn" {
  value = "${aws_apigatewayv2_api.dashboard.execution_arn}/$default/GET/dashboard/q3/households"
}

resource "aws_apigatewayv2_route" "dashboard_q1" {
  api_id             = aws_apigatewayv2_api.dashboard.id
  route_key          = "GET /dashboard/q1"
  target             = "integrations/${aws_apigatewayv2_integration.dashboard_q3.id}"
  authorization_type = "AWS_IAM"
}

resource "aws_lambda_permission" "dashboard_q1" {
  statement_id  = "AllowGatewayQ1"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dashboard_query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.dashboard.execution_arn}/$default/GET/dashboard/q1"
}

output "dashboard_q1_api_url" {
  value = "${aws_apigatewayv2_api.dashboard.api_endpoint}/dashboard/q1"
}

output "dashboard_q1_invoke_arn" {
  value = "${aws_apigatewayv2_api.dashboard.execution_arn}/$default/GET/dashboard/q1"
}
