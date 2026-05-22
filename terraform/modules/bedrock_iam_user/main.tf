locals {
  base_tags = {
    UserType   = "System"
    APPACCESS  = var.APPACCESS
    GROUP      = var.GROUP
    COSTCENTER = var.COSTCENTER
    Note       = var.Note
  }
  contact_tag = var.Contact != "" ? { Contact = var.Contact } : {}
  tags        = merge(local.base_tags, local.contact_tag)
}

# IAM user for LLM application Bedrock access. Terraform creates the user,
# attaches the invoke policy, and applies mandatory tags. Credential issuance
# (Bedrock API keys, IAM access keys, STS assume-role) is out of band — keys
# require rotation and are not managed by this module.
resource "aws_iam_user" "this" {
  name = var.name
  path = var.path
  tags = local.tags
}

resource "aws_iam_user_policy_attachment" "bedrock" {
  user       = aws_iam_user.this.name
  policy_arn = var.policy_arn
}
