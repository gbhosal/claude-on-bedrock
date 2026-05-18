module "system_users" {
  for_each = var.llm_apps
  source   = "./modules/bedrock_iam_user"

  name       = each.key
  UserType   = "System"
  APPACCESS  = each.value.APPACCESS
  GROUP      = each.value.GROUP
  COSTCENTER = each.value.COSTCENTER
  Note       = each.value.Note
  Contact    = each.value.Contact
  policy_arn = aws_iam_policy.bedrock_invoke.arn
}
