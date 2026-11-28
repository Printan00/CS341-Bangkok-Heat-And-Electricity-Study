variable "vercel_team_slug" {
  description = "Vercel team slug used by the OIDC issuer (https://oidc.vercel.com/<slug>)"
  type        = string
  default     = "suphanatchanleks-projects"
}

variable "vercel_project_name" {
  description = "Vercel project that may assume the dashboard role"
  type        = string
  default     = "frontend"
}

locals {
  vercel_issuer_host = "oidc.vercel.com/${var.vercel_team_slug}"
}

resource "aws_iam_openid_connect_provider" "vercel" {
  url            = "https://${local.vercel_issuer_host}"
  client_id_list = ["https://vercel.com/${var.vercel_team_slug}"]
}

data "aws_iam_policy_document" "vercel_dashboard_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.vercel.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.vercel_issuer_host}:aud"
      values   = ["https://vercel.com/${var.vercel_team_slug}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.vercel_issuer_host}:sub"
      values = [
        for env in ["production", "preview"] :
        "owner:${var.vercel_team_slug}:project:${var.vercel_project_name}:environment:${env}"
      ]
    }
  }
}

resource "aws_iam_role" "vercel_dashboard" {
  name               = "${var.project}-vercel-dashboard"
  assume_role_policy = data.aws_iam_policy_document.vercel_dashboard_trust.json
}

# Summary and household-level routes for Q1-Q3.
resource "aws_iam_role_policy" "vercel_dashboard_invoke" {
  name = "invoke-dashboard-summary"
  role = aws_iam_role.vercel_dashboard.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "execute-api:Invoke"
      Resource = [
        for path in ["q1", "q2", "q3", "q2/households", "q3/households"] :
        "${aws_apigatewayv2_api.dashboard.execution_arn}/$default/GET/dashboard/${path}"
      ]
    }]
  })
}

output "vercel_dashboard_role_arn" {
  value = aws_iam_role.vercel_dashboard.arn
}
