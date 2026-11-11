variable "region" {
  description = "AWS region for every resource"
  type        = string
  default     = "ap-southeast-1"
}

variable "project" {
  description = "Prefix for resource names"
  type        = string
  default     = "bhes"
}

# AWS-managed layer with pandas + pyarrow (AWS SDK for pandas 3.16.1, Python 3.13), published for
# ap-southeast-1. Change the region part if var.region changes; versions are listed in the
# AWS SDK for pandas docs ("AWS Lambda Managed Layers").
variable "pandas_layer_arn" {
  description = "Lambda layer that provides pyarrow for the Parquet steps"
  type        = string
  default     = "arn:aws:lambda:ap-southeast-1:336392948345:layer:AWSSDKPandas-Python313:12"
}
