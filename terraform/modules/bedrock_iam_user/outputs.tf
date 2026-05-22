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
