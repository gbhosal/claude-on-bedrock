# Credential Strategy: Short-term vs Long-term Keys

This document covers authentication methods for **LLM applications** calling AWS Bedrock. Use the decision guide in [README.md](README.md) to pick the right method.

> **Not covered here:** Claude Code (the `claude` CLI). Do not route Claude Code through Bedrock — see [README.md](README.md#do-not-use-claude-code-on-bedrock) for cost rationale and alternatives.

---

## Method 0: Terraform-Managed IAM Users (Identity Only) {#terraform-managed}

**When to use**: Every LLM application that needs a dedicated Bedrock identity in AWS.

**What Terraform does**: Creates the IAM user, attaches the Bedrock invoke policy, and applies five mandatory tags. See [`terraform/`](terraform/) and [`06-iam-lifecycle.md`](06-iam-lifecycle.md).

**What Terraform does not do**: Create Bedrock API keys, IAM access keys, or Secrets Manager secrets. Credentials require rotation and are provisioned by the app team outside Terraform.

Key points:
- LLM app users are named after the app (`app-<name>`) and tagged `UserType=System`
- All five mandatory tags (`UserType`, `APPACCESS`, `GROUP`, `COSTCENTER`, `Note`) are enforced by Terraform validation
- Individual developer IAM users are **not** onboarded through this module — use AWS SSO (Method 3) for local development

**Migration target**: Move from out-of-band Bedrock API keys to instance/task roles (Method 5) over time.

---

## Method 1: Static Long-term IAM Keys {#static}

> **Not used in this organisation.** Static `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` credentials are not provisioned via Terraform. Use Method 0 (Terraform-managed IAM user) for identity, then provision rotated credentials out of band or migrate to Method 5 (instance role).

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

1. After `terraform apply` creates the IAM user, create a Bedrock API key in the AWS console under **Amazon Bedrock → API keys** (or via your org's credential rotation tooling), scoped to that user.
2. Store the key in your app's secret store (Secrets Manager path managed by your rotation pipeline — not by Terraform).
3. Set environment variables before running your application:

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
| Terraform IAM user (identity only) | N/A — no credentials created | N/A | LLM app identity in AWS | Yes (identity) |
| STS temporary credentials | 15 min – 36 hours | Automatic | CI/CD, cross-account | Yes |
| AWS SSO / Identity Center | Hours (session) | Automatic | Local SDK development | Yes |
| Bedrock API Keys | Until revoked | Manual | Apps outside AWS (transitional) | With caution |
| Instance/task IAM role | Minutes (auto-rotate) | Automatic | AWS-hosted LLM workloads | Yes (best) |
