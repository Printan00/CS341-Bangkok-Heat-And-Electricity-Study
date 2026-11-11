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
