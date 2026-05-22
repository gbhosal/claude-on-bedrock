variable "name" {
  description = "IAM username for the LLM app (e.g. app-ragbot-bedrock)."
  type        = string
  validation {
    condition     = length(trimspace(var.name)) > 0
    error_message = "name must not be empty."
  }
}

variable "APPACCESS" {
  description = "APPACCESS tag — describes the access purpose, e.g. \"rag\", \"codegen\"."
  type        = string
  validation {
    condition     = length(trimspace(var.APPACCESS)) > 0
    error_message = "APPACCESS must not be empty."
  }
}

variable "GROUP" {
  description = "GROUP tag — the owning team name."
  type        = string
  validation {
    condition     = length(trimspace(var.GROUP)) > 0
    error_message = "GROUP must not be empty."
  }
}

variable "COSTCENTER" {
  description = "COSTCENTER tag — cost allocation code."
  type        = string
  validation {
    condition     = length(trimspace(var.COSTCENTER)) > 0
    error_message = "COSTCENTER must not be empty."
  }
}

variable "Note" {
  description = "Note tag — free-text comments about the user or app team."
  type        = string
  validation {
    condition     = length(trimspace(var.Note)) > 0
    error_message = "Note must not be empty."
  }
}

variable "Contact" {
  description = "Contact tag — email address for rotation and decommission notifications. Optional but strongly recommended."
  type        = string
  default     = ""
}

variable "policy_arn" {
  description = "ARN of the IAM policy to attach to this user (e.g. the Bedrock invoke policy)."
  type        = string
}

variable "path" {
  description = "IAM path for the user. Defaults to /bedrock/."
  type        = string
  default     = "/bedrock/"
}
