resource "aws_glue_catalog_database" "bhes" {
  name = var.project
}

# Run on demand (console or `aws glue start-crawler`) after a batch lands in curated/
resource "aws_glue_crawler" "curated" {
  name          = "${var.project}-curated"
  role          = aws_iam_role.glue_crawler.arn
  database_name = aws_glue_catalog_database.bhes.name

  # One table per folder: s3://lake/curated/<table>/ (bucket=1, curated=2, table=3)
  configuration = jsonencode({ Version = 1.0, Grouping = { TableLevelConfiguration = 3 } })

  s3_target {
    path = "s3://${aws_s3_bucket.lake.bucket}/curated/"
  }
}

resource "aws_athena_workgroup" "bhes" {
  name          = "${var.project}-wg"
  force_destroy = true # only drops saved query history, not data

  configuration {
    enforce_workgroup_configuration = true
    bytes_scanned_cutoff_per_query  = 1073741824 # 1 GB cap per query to bound cost

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/"
    }
  }
}
