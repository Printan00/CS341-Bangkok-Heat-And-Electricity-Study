output "lake_bucket" {
  value = aws_s3_bucket.lake.bucket
}

output "athena_results_bucket" {
  value = aws_s3_bucket.athena_results.bucket
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda.arn
}

output "sfn_role_arn" {
  value = aws_iam_role.sfn.arn
}

output "glue_crawler_role_arn" {
  value = aws_iam_role.glue_crawler.arn
}

output "athena_query_policy_arn" {
  value = aws_iam_policy.athena_query.arn
}

output "state_machine_arn" {
  value = aws_sfn_state_machine.pipeline.arn
}

output "glue_crawler" {
  value = aws_glue_crawler.curated.name
}

output "athena_workgroup" {
  value = aws_athena_workgroup.bhes.name
}
