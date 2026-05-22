variable "aws_region" {
  description = "AWS region where IAM users and the Bedrock policy are created."
  type        = string
  default     = "us-east-1"
}

variable "llm_apps" {
  description = <<-EOT
    Map of IAM users for LLM applications.
    Key = IAM username (use the app name, e.g. "app-ragbot-bedrock").
    All tag fields except Contact are mandatory; keys are case-sensitive.
    Terraform creates the user and attaches the Bedrock policy only — credentials
    are provisioned and rotated outside Terraform.
  EOT
  type = map(object({
    APPACCESS  = string
    GROUP      = string
    COSTCENTER = string
    Note       = string
    Contact    = optional(string, "")
  }))
  default = {}
}
