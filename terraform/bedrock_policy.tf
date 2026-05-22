# Terraform-managed version of examples/settings/iam_policy.json.
# This is the single source of truth for the Bedrock invoke policy once
# you adopt the Terraform workflow.
resource "aws_iam_policy" "bedrock_invoke" {
  name        = "BedrockInvokePolicy"
  path        = "/bedrock/"
  description = "Minimum permissions for Anthropic SDK and boto3 access to AWS Bedrock."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockInvokeAndProfile"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ListInferenceProfiles",
          "bedrock:GetInferenceProfile",
        ]
        Resource = [
          "arn:aws:bedrock:*:*:inference-profile/*",
          "arn:aws:bedrock:*:*:application-inference-profile/*",
          "arn:aws:bedrock:*:*:foundation-model/*",
        ]
      }
    ]
  })
}
