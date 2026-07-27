terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # NOTE: local state for now (gitignored). Production upgrade = S3 backend +
  # DynamoDB lock. Fine for a solo project as long as terraform.tfstate is kept.
}
