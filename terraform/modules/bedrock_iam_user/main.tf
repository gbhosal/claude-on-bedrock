locals {
  base_tags = {
    UserType   = var.UserType
    APPACCESS  = var.APPACCESS
    GROUP      = var.GROUP
    COSTCENTER = var.COSTCENTER
    Note       = var.Note
  }
  contact_tag = var.Contact != "" ? { Contact = var.Contact } : {}
  tags        = merge(local.base_tags, local.contact_tag)
}

# IAM user is retained for LDAP lifecycle management, tagging, and future
# migration to short-term credentials. The Bedrock API key below is what
# the user actually authenticates with.
resource "aws_iam_user" "this" {
  name = var.name
  path = var.path
  tags = local.tags
}

resource "aws_iam_user_policy_attachment" "bedrock" {
  user       = aws_iam_user.this.name
  policy_arn = var.policy_arn
}

# Individuals: a time_rotating resource tracks the 30-day rotation window.
# When it fires, replace_triggered_by below forces a new Bedrock API key.
# System users: count = 0 — no rotation resource, key never expires.
resource "time_rotating" "key_rotation" {
  count         = var.UserType == "Individual" ? 1 : 0
  rotation_days = 30
}

resource "aws_bedrock_api_key" "this" {
  name        = var.name
  description = "${var.UserType} Bedrock API key for ${var.name}. ${var.UserType == "Individual" ? "Rotates every 30 days." : "No expiry — decommission with app."}"

  # Individuals: expires_at is set to the next rotation timestamp (30 days out).
  # System users: no expires_at — the attribute is omitted when null.
  expires_at = var.UserType == "Individual" ? time_rotating.key_rotation[0].rotation_rfc3339 : null

  lifecycle {
    # When time_rotating triggers at day 30, recreate the Bedrock API key
    # so the new key's expires_at advances another 30 days.
    # For System users count = 0, so this list is empty and never fires.
    replace_triggered_by = [time_rotating.key_rotation]
  }
}

resource "aws_secretsmanager_secret" "credentials" {
  name        = "iam/bedrock/${var.name}"
  description = "Bedrock API key credentials for ${var.UserType} ${var.name}."
  tags        = local.tags
}

resource "aws_secretsmanager_secret_version" "credentials" {
  secret_id = aws_secretsmanager_secret.credentials.id

  secret_string = jsonencode({
    bedrock_api_key    = aws_bedrock_api_key.this.api_key
    bedrock_api_key_id = aws_bedrock_api_key.this.id
  })
}
