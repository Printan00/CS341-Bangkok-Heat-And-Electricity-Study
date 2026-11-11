output "lake_bucket" {
  value = aws_s3_bucket.lake.bucket
}

output "athena_results_bucket" {
  value = aws_s3_bucket.athena_results.bucket
}
