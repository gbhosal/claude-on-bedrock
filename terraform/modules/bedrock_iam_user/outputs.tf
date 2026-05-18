output "user_name" {
  description = "IAM username."
  value       = aws_iam_user.this.name
}

output "user_arn" {
  description = "ARN of the IAM user."
  value       = aws_iam_user.this.arn
}

output "user_unique_id" {
  description = "Stable unique ID of the IAM user (does not change on rename)."
  value       = aws_iam_user.this.unique_id
}

output "bedrock_api_key_id" {
  description = "Bedrock API key identifier (non-secret, safe to log)."
  value       = aws_bedrock_api_key.this.id
}

output "secret_name" {
  description = "Secrets Manager secret name: iam/bedrock/<username>."
  value       = aws_secretsmanager_secret.credentials.name
}

output "secret_arn" {
  description = "Secrets Manager secret ARN for the Bedrock API key credentials."
  value       = aws_secretsmanager_secret.credentials.arn
}
