output "bedrock_policy_arn" {
  description = "ARN of the shared Bedrock invoke IAM policy."
  value       = aws_iam_policy.bedrock_invoke.arn
}

output "llm_app_user_arns" {
  description = "ARNs of LLM application IAM users, keyed by IAM username."
  value       = { for k, v in module.llm_app_users : k => v.user_arn }
}

output "llm_app_user_names" {
  description = "IAM usernames for LLM applications, keyed by tfvars entry key."
  value       = { for k, v in module.llm_app_users : k => v.user_name }
}
