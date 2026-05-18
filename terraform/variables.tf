variable "aws_region" {
  description = "AWS region where IAM users and the Bedrock policy are created."
  type        = string
  default     = "us-east-1"
}

# ---------------------------------------------------------------------------
# Individual (individual developer) users
# IAM username = LDAP username so the LDAP sync tool can do a direct match.
# ---------------------------------------------------------------------------
variable "developers" {
  description = <<-EOT
    Map of individual (Individual) users.
    Key = IAM username (must match the person's LDAP/directory username exactly).
    All tag fields except Contact are mandatory; keys are case-sensitive.
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

# ---------------------------------------------------------------------------
# System users for LLM applications
# IAM username = app name so ownership is self-evident.
# ---------------------------------------------------------------------------
variable "llm_apps" {
  description = <<-EOT
    Map of System (application) users.
    Key = IAM username (use the app name, e.g. "app-ragbot-bedrock").
    All tag fields except Contact are mandatory; keys are case-sensitive.
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
