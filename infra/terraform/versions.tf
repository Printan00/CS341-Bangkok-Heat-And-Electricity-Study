terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # State bucket is created once by hand (see README "Deploy / Destroy") so destroy can't delete its own state.
  backend "s3" {
    bucket       = "bhes-tfstate-334177992720"
    key          = "bhes/terraform.tfstate"
    region       = "ap-southeast-1"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = var.project
    }
  }
}
