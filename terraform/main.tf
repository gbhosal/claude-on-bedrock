terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.97"   # aws_bedrock_api_key added in 5.97
    }
    time = {
      source  = "hashicorp/time"
      version = ">= 0.11"   # time_rotating with rotation_rfc3339 attribute
    }
  }

  # Replace with your backend — S3 example shown:
  # backend "s3" {
  #   bucket = "my-tf-state"
  #   key    = "bedrock-iam/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}
