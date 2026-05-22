# Credential Strategy for LLM Applications

This document covers how **LLM applications** authenticate to AWS Bedrock. Use the decision guide in [README.md](README.md) to pick the right method.

> **Not covered here:** Claude Code (the `claude` CLI). Do not route Claude Code through Bedrock — see [README.md](README.md#do-not-use-claude-code-on-bedrock) for cost rationale and alternatives.

---

## Method 0: Terraform-Managed IAM Users (Identity Only) {#terraform-managed}

**When to use**: Every LLM application that needs a dedicated Bedrock identity in AWS.

**What Terraform does**: Creates the IAM user, attaches the Bedrock invoke policy, and applies five mandatory tags. See [`terraform/`](terraform/) and [`06-iam-lifecycle.md`](06-iam-lifecycle.md).

**What Terraform does not do**: Create Bedrock API keys or Secrets Manager secrets. Keys are provisioned and rotated by the platform team.

Key points:
- LLM app users are named after the app (`app-<name>`) and tagged `UserType=System`
- All five mandatory tags (`UserType`, `APPACCESS`, `GROUP`, `COSTCENTER`, `Note`) are enforced by Terraform validation
- Applications authenticate with a **Bedrock API key** (`AWS_BEARER_TOKEN_BEDROCK`) until migrated to an instance/task IAM role

**Migration target**: Move AWS-hosted workloads from Bedrock API keys to instance/task roles (Method 2).

---

## Method 1: Bedrock API Keys {#bedrock-api-keys}

**When to use**: LLM applications that run outside AWS, or any app not yet using an instance/task IAM role. This is the **default** authentication method for app teams today.

**Benefit**: Single token, scoped to Bedrock only, simpler than full IAM access keys.

### Setup

1. Platform team provisions a Bedrock API key scoped to your app's Terraform IAM user.
2. Store the key in your app's secret store and inject at runtime:

```bash
export AWS_BEARER_TOKEN_BEDROCK=your-bedrock-api-key
export AWS_REGION=us-east-1
```

Use **`AWS_BEARER_TOKEN_BEDROCK`** exactly — not `AWS_BEARER_TOKEN`. No `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` needed.

The Anthropic SDK and `@anthropic-ai/bedrock-sdk` pick up the environment variable automatically:

```python
from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(aws_region="us-east-1")
```

Keys are rotated by the platform team. When you receive a new key, update your secret store and redeploy.

---

## Method 2: EC2 / ECS / Lambda Instance Role {#instance-role}

**When to use**: LLM workloads running on AWS — EC2, ECS, Lambda, EKS. **Target state for production.**

**Benefit**: No long-lived secrets. The AWS SDK fetches credentials from instance metadata automatically.

### Setup

1. Attach an IAM role to your compute with the Bedrock policy from [02-iam-permissions.md](02-iam-permissions.md).
2. No `AWS_BEARER_TOKEN_BEDROCK` needed — only set `AWS_REGION` if required.

```python
from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(aws_region="us-east-1")
```

---

## Comparison Summary

| Method | Best for | Env vars |
|--------|----------|----------|
| Terraform IAM user (identity only) | Per-app Bedrock identity in AWS | None — identity only |
| Bedrock API key | Apps outside AWS; transitional | `AWS_BEARER_TOKEN_BEDROCK`, `AWS_REGION` |
| Instance/task IAM role | AWS-hosted production workloads | `AWS_REGION` (optional) |
