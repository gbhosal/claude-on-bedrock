output "bedrock_policy_arn" {
  description = "ARN of the shared Bedrock invoke IAM policy."
  value       = aws_iam_policy.bedrock_invoke.arn
}

output "associate_user_arns" {
  description = "ARNs of all Individual (individual developer) IAM users."
  value       = { for k, v in module.associate_users : k => v.user_arn }
}

output "system_user_arns" {
  description = "ARNs of all System (LLM app) IAM users."
  value       = { for k, v in module.system_users : k => v.user_arn }
}

output "associate_secret_arns" {
  description = "Secrets Manager ARNs for Individual user credentials, keyed by IAM username."
  value       = { for k, v in module.associate_users : k => v.secret_arn }
}

output "system_secret_arns" {
  description = "Secrets Manager ARNs for System user credentials, keyed by IAM username."
  value       = { for k, v in module.system_users : k => v.secret_arn }
}
