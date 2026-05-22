# Credential Strategy: Short-term vs Long-term Keys

This document covers authentication methods for **LLM applications** calling AWS Bedrock. Use the decision guide in [README.md](README.md) to pick the right method.

> **Not covered here:** Claude Code (the `claude` CLI). Do not route Claude Code through Bedrock — see [README.md](README.md#do-not-use-claude-code-on-bedrock) for cost rationale and alternatives.

---

## Method 0: Terraform-Managed Long-term Keys (Transitional) {#terraform-managed}

**When to use**: LLM apps migrating from Anthropic Console that need a governed, auditable starting point before adopting short-term credentials or instance roles.

**How it differs from Method 1**: Every user is created by Terraform (not the console), carries five mandatory tags, and is enrolled in LDAP-driven deactivation for individual developer accounts.

**Setup**: See [`terraform/`](terraform/) and [`06-iam-lifecycle.md`](06-iam-lifecycle.md) for the full workflow.

Key points:
- IAM username for individuals **must match** the person's LDAP username exactly — this is what the deactivation tool uses to match
- LLM app users are named after the app (`app-<name>`) and tagged `UserType=System` — they are **not** checked against LDAP
- Individual (`UserType=Individual`) keys are for **local SDK development and integration testing only**, not for Claude Code CLI
- All five mandatory tags (`UserType`, `APPACCESS`, `GROUP`, `COSTCENTER`, `Note`) are enforced by Terraform validation
- Deactivation disables keys (`Inactive` status) rather than deleting users, preserving CloudTrail history

**Migration target**: Move `Individual` users to AWS SSO (Method 3) and `System` users to instance/task roles (Method 5) over time.

---

## Method 1: Static Long-term IAM Keys {#static}

> **Not used in this organisation.** This method is documented as a potential approach for awareness only. Static `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` credentials are not provisioned or supported. Use Method 0 (Terraform-managed Bedrock API keys) as the governed starting point, and migrate toward Method 3 (SSO) or Method 5 (instance role) over time.

**Why not**: Keys never expire, cannot be scoped to a rotation window, and carry a high blast-radius if leaked (committed to git, written to logs, etc.). All long-term credential needs are met by Terraform-managed Bedrock API keys stored in Secrets Manager, which provide a narrower token surface and an enforced 30-day rotation for individuals.

---

## Method 2: Temporary STS Credentials (Short-term Keys) {#sts}

**When to use**: CI/CD pipelines, cross-account access, MFA-protected operations, any scenario requiring time-limited access.

**Benefit**: Credentials expire automatically (15 minutes to 36 hours). A leaked token self-destructs.

### How STS Works

STS (Security Token Service) issues temporary credentials that include a session token. The three-part set expires after a configured duration:

```bash
export AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE      # starts with ASIA (temporary)
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=AQoXnyc4lcK4w...           # required for temporary creds
export AWS_REGION=us-east-1
```

### Obtaining Temporary Credentials

**Via AssumeRole** (most common in CI/CD):
```bash
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/BedrockAccessRole \
  --role-session-name my-session \
  --duration-seconds 3600
```

**Via GetSessionToken** (MFA-protected):
```bash
aws sts get-session-token \
  --serial-number arn:aws:iam::123456789012:mfa/my-mfa-device \
  --token-code 123456 \
  --duration-seconds 43200
```

**Export the result in one command:**
```bash
eval $(aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/BedrockAccessRole \
  --role-session-name cli-session \
  --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' \
  --output text | awk '{print "export AWS_ACCESS_KEY_ID="$1"\nexport AWS_SECRET_ACCESS_KEY="$2"\nexport AWS_SESSION_TOKEN="$3}')
```

### Using STS credentials in application code

The Anthropic SDK and boto3 pick up standard AWS credential environment variables automatically:

```python
import os
import anthropic

# Credentials already exported from STS assume-role
client = anthropic.AnthropicBedrockMantle(aws_region=os.environ["AWS_REGION"])
```

---

## Method 3: AWS SSO / IAM Identity Center {#sso}

**When to use**: Individual developers running LLM application code locally against Bedrock during development and integration testing.

**Benefit**: Browser-based authentication, credentials auto-rotate, central access management, no stored secrets.

### Setup

**Step 1 — Configure SSO profile (one-time)**:
```bash
aws configure sso
```
Follow prompts to enter:
- SSO start URL (e.g., `https://mycompany.awsapps.com/start`)
- SSO region
- AWS account ID and role name
- Profile name (e.g., `bedrock-dev`)

**Step 2 — Login** (opens browser):
```bash
aws sso login --profile bedrock-dev
```

**Step 3 — Run your application locally**:
```bash
export AWS_PROFILE=bedrock-dev
export AWS_REGION=us-east-1
python examples/python/basic_chat.py
```

SSO tokens expire (typically 8 hours). Re-run `aws sso login` when credentials expire.

---

## Method 4: Bedrock API Keys {#bedrock-api-keys}

**When to use**: LLM applications deployed outside AWS that cannot yet use instance roles, or quick prototyping.

**Benefit**: Single token, simpler credential management than full IAM user keys.

**Limitation**: Narrower IAM policies may cause additional retries when resolving inference profile ARNs (requests still succeed). For production, grant `bedrock:GetInferenceProfile` to the API key's policy.

### Setup

1. Retrieve the Bedrock API key from Secrets Manager at `iam/bedrock/<app-name>` (provisioned by Terraform), or create one in the AWS console under Amazon Bedrock → API keys.
2. Set environment variables before running your application:

```bash
export AWS_BEARER_TOKEN_BEDROCK=your-bedrock-api-key
export AWS_REGION=us-east-1
```

No `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` needed.

---

## Method 5: EC2 / ECS Instance Metadata (No Credentials) {#instance-role}

**When to use**: Any LLM workload running inside AWS — EC2 instances, ECS tasks, Lambda functions, EKS pods. **This is the target state for production LLM applications.**

**Benefit**: Zero credential management. The AWS SDK automatically fetches credentials from the instance metadata service. Credentials rotate automatically.

### Setup

1. Attach an IAM role to your EC2 instance, ECS task definition, or Lambda function with the Bedrock policy from [02-iam-permissions.md](02-iam-permissions.md).
2. No environment variables needed — the AWS SDK credential chain picks up the role automatically.

```python
import anthropic

# No credentials in code or env — instance role is used automatically
client = anthropic.AnthropicBedrockMantle(aws_region="us-east-1")
```

---

## Comparison Summary

| Method | Key Lifetime | Rotation | Best For | Production Safe? |
|--------|-------------|----------|----------|-----------------|
| ~~Static long-term IAM keys~~ | Never (manual revoke) | Manual | **Not used** — see Method 1 note | No |
| STS temporary credentials | 15 min – 36 hours | Automatic | CI/CD, cross-account | Yes |
| AWS SSO / Identity Center | Hours (session) | Automatic | Local SDK development | Yes |
| Bedrock API Keys | Until revoked | Manual | Apps outside AWS (transitional) | With caution |
| Instance/task IAM role | Minutes (auto-rotate) | Automatic | AWS-hosted LLM workloads | Yes (best) |
