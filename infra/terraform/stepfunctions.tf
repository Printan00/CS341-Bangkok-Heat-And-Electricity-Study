# CheckBatch → (already done? stop) → Validate → (valid? else fail) → Transform → Integrate → Verify.
# A Lambda error fails the execution at that step; the failed step shows in the console and its log in CloudWatch.
locals {
  fn = { for k, f in aws_lambda_function.step : k => f.arn }
}

resource "aws_sfn_state_machine" "pipeline" {
  name     = "${var.project}-pipeline"
  role_arn = aws_iam_role.sfn.arn

  definition = jsonencode({
    Comment = "BHES batch pipeline"
    StartAt = "CheckBatch"
    States = {
      CheckBatch = { Type = "Task", Resource = local.fn["check_batch"], Next = "AlreadyDone?" }
      "AlreadyDone?" = {
        Type    = "Choice"
        Choices = [{ Variable = "$.already_done", BooleanEquals = true, Next = "SkipDuplicate" }]
        Default = "Validate"
      }
      SkipDuplicate = { Type = "Succeed" }
      Validate      = { Type = "Task", Resource = local.fn["validate"], Next = "Valid?" }
      "Valid?" = {
        Type    = "Choice"
        Choices = [{ Variable = "$.valid", BooleanEquals = false, Next = "ValidationFailed" }]
        Default = "Transform"
      }
      ValidationFailed = { Type = "Fail", Error = "ValidationFailed", Cause = "Batch failed validation; see quarantine/" }
      Transform        = { Type = "Task", Resource = local.fn["transform"], Next = "Integrate" }
      Integrate        = { Type = "Task", Resource = local.fn["integrate"], Next = "Verify" }
      Verify           = { Type = "Task", Resource = local.fn["verify"], End = true }
    }
  })
}
