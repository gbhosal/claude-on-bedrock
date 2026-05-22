# IAM Permissions for AWS Bedrock + Claude

## Minimal IAM Policy

Attach this policy to the IAM user, role, or identity used to access Bedrock. This is the minimum required for Claude Code CLI and SDK usage.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvokeAndProfile",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListInferenceProfiles",
        "bedrock:GetInferenceProfile"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:inference-profile/*",
        "arn:aws:bedrock:*:*:application-inference-profile/*",
        "arn:aws:bedrock:*:*:foundation-model/*"
      ]
    }
  ]
}
```

A ready-to-use copy is at [examples/settings/iam_policy.json](examples/settings/iam_policy.json).

## What Each Action Does

| Action | Required For | Notes |
|--------|-------------|-------|
| `bedrock:InvokeModel` | Synchronous model calls | Required for non-streaming requests |
| `bedrock:InvokeModelWithResponseStream` | Streaming responses | Required for streaming; Claude Code uses this heavily |
| `bedrock:ListInferenceProfiles` | Model discovery | Claude Code uses this to enumerate available models at startup |
| `bedrock:GetInferenceProfile` | ARN resolution | Resolves application inference profile ARNs to foundation models; required when using cross-region profiles |

## First-Time Account Setup (One-Time)

> **No longer required.** AWS previously required submitting a use case via `bedrock:PutUseCaseForModelAccess` before models could be used. This step has been removed — models are automatically enabled. The `BedrockFirstTimeSetup` policy and its actions (`PutUseCaseForModelAccess`, `GetUseCaseForModelAccess`) do not need to be included in any user or role policy.

## Model Access Enablement

As of the latest AWS update, Claude models on Bedrock are **automatically enabled** — no manual opt-in step is required. You can invoke any available model as soon as your IAM policy is in place.

You can verify available models in your region with:

```bash
aws bedrock list-foundation-models \
  --by-provider Anthropic \
  --region us-east-1 \
  --query 'modelSummaries[].{Name:modelName,ID:modelId,Status:modelLifecycle.status}' \
  --output table
```

## Scoping to Specific Models (Tighter Security)

To restrict access to only specific models, replace the wildcard `Resource` with specific ARNs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvokeSpecificModels",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-opus-4-7",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0"
      ]
    },
    {
      "Sid": "BedrockProfileAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:ListInferenceProfiles",
        "bedrock:GetInferenceProfile"
      ],
      "Resource": "*"
    }
  ]
}
```

## Policy for CI/CD Pipelines (Assumed Role)

For CI/CD, create a dedicated role rather than a user. The pipeline assumes this role via STS:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockCICD",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:GetInferenceProfile"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1:*:inference-profile/*",
        "arn:aws:bedrock:us-east-1::foundation-model/*"
      ]
    }
  ]
}
```

Trust policy for the role (allows your CI/CD AWS account to assume it):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::CICD_ACCOUNT_ID:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "your-external-id"
        }
      }
    }
  ]
}
```

## Terraform Module

The policy in this document is also managed as an `aws_iam_policy` resource in [`terraform/bedrock_policy.tf`](terraform/bedrock_policy.tf). When using the Terraform-managed IAM user workflow (see [07-iam-lifecycle.md](07-iam-lifecycle.md)), `terraform/bedrock_policy.tf` is the single source of truth — manual updates to `examples/settings/iam_policy.json` will not affect users managed by Terraform.

The Terraform module at [`terraform/modules/bedrock_iam_user/`](terraform/modules/bedrock_iam_user/) creates IAM users, attaches this policy, and enforces all five mandatory tags. See [`terraform/terraform.tfvars.example`](terraform/terraform.tfvars.example) for the full variable structure.

---

## Verify Your Permissions

Test that your credentials have the right access:
```bash
# Test invoking a model
aws bedrock-runtime invoke-model \
  --region us-east-1 \
  --model-id anthropic.claude-haiku-4-5-20251001-v1:0 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/bedrock-test.json && cat /tmp/bedrock-test.json

# List available inference profiles
aws bedrock list-inference-profiles --region us-east-1 \
  --query 'inferenceProfileSummaries[?contains(inferenceProfileId, `anthropic`)].[inferenceProfileId,status]' \
  --output table
```
