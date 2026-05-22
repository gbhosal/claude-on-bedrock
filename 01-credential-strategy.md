# Credential Strategy: Short-term vs Long-term Keys

## Overview of Auth Methods

AWS Bedrock supports five authentication approaches. Use the decision guide in [README.md](README.md) to pick the right one, then follow the setup steps below.

---

## Method 0: Terraform-Managed Long-term Keys (Transitional) {#terraform-managed}

**When to use**: Teams migrating from Anthropic Console who need a governed, auditable starting point before adopting short-term credentials. This is the only acceptable form of long-term key usage beyond individual dev/test machines.

**How it differs from Method 1**: Every user is created by Terraform (not the console), carries five mandatory tags, and is enrolled in LDAP-driven deactivation so keys are disabled automatically when someone leaves the organization.

**Setup**: See [`terraform/`](terraform/) and [`07-iam-lifecycle.md`](07-iam-lifecycle.md) for the full workflow.

Key points:
- IAM username for individuals **must match** the person's LDAP username exactly — this is what the deactivation tool uses to match
- LLM app users are named after the app (`app-<name>`) and tagged `UserType=System` — they are **not** checked against LDAP
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
export CLAUDE_CODE_USE_BEDROCK=1
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

---

## Method 3: AWS SSO / IAM Identity Center {#sso}

**When to use**: Enterprise environments, teams using AWS Organizations. The recommended method for individual developers.

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
- Profile name (e.g., `bedrock-prod`)

**Step 2 — Login** (opens browser):
```bash
aws sso login --profile bedrock-prod
```

**Step 3 — Use with Claude Code**:
```bash
export AWS_PROFILE=bedrock-prod
export AWS_REGION=us-east-1
export CLAUDE_CODE_USE_BEDROCK=1
claude
```

### Auto-refresh with Claude Code settings

SSO tokens expire (typically 8 hours). Configure `~/.claude/settings.json` to re-authenticate automatically:

```json
{
  "awsAuthRefresh": "aws sso login --profile bedrock-prod",
  "env": {
    "AWS_PROFILE": "bedrock-prod",
    "AWS_REGION": "us-east-1",
    "CLAUDE_CODE_USE_BEDROCK": "1"
  }
}
```

When Claude Code detects expired credentials, it triggers `awsAuthRefresh` and opens the browser for re-authentication.

See also: [examples/settings/settings_sso.json](examples/settings/settings_sso.json) for a copy-paste template.

---

## Method 4: Bedrock API Keys {#bedrock-api-keys}

**When to use**: Simplified setup when you don't need full AWS IAM, quick prototyping, or when sharing access without provisioning IAM users.

**Benefit**: Single token, no AWS account setup required for the end user.

**Limitation**: Narrower IAM policies may cause additional retries when resolving inference profile ARNs (requests still succeed). For production, grant `bedrock:GetInferenceProfile` to the API key's policy.

### Setup

1. Create a Bedrock API key in the AWS console under Amazon Bedrock → API keys.
2. Set environment variable:

```bash
export AWS_BEARER_TOKEN_BEDROCK=your-bedrock-api-key
export AWS_REGION=us-east-1
export CLAUDE_CODE_USE_BEDROCK=1
```

No `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` needed.

---

## Method 5: EC2 / ECS Instance Metadata (No Credentials) {#instance-role}

**When to use**: Any workload running inside AWS — EC2 instances, ECS tasks, Lambda functions, EKS pods.

**Benefit**: Zero credential management. The AWS SDK automatically fetches credentials from the instance metadata service. Credentials rotate automatically.

### Setup

1. Attach an IAM role to your EC2 instance, ECS task definition, or Lambda function with the Bedrock policy from [03-iam-permissions.md](03-iam-permissions.md).
2. No environment variables needed — the AWS SDK credential chain picks up the role automatically.

For Claude Code on an EC2 instance:
```bash
export AWS_REGION=us-east-1
export CLAUDE_CODE_USE_BEDROCK=1
# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are NOT needed
claude
```

---

## Comparison Summary

| Method | Key Lifetime | Rotation | Best For | Production Safe? |
|--------|-------------|----------|----------|-----------------|
| ~~Static long-term IAM keys~~ | Never (manual revoke) | Manual | **Not used** — see Method 1 note | No |
| STS temporary credentials | 15 min – 36 hours | Automatic | CI/CD, cross-account | Yes |
| AWS SSO / Identity Center | Hours (session) | Automatic | Individual developers | Yes |
| Bedrock API Keys | Until revoked | Manual | Quick prototyping | With caution |
| Instance/task IAM role | Minutes (auto-rotate) | Automatic | AWS-hosted workloads | Yes (best) |

## awsCredentialExport Hook (Advanced)

For custom credential pipelines (e.g., Vault, custom STS wrappers), use `awsCredentialExport` in `~/.claude/settings.json`. This runs at session start and on each reload, outputting a JSON credential object:

```json
{
  "awsCredentialExport": "my-credential-helper --output json",
  "env": {
    "AWS_REGION": "us-east-1",
    "CLAUDE_CODE_USE_BEDROCK": "1"
  }
}
```

The helper must output JSON in this format:
```json
{
  "AccessKeyId": "ASIA...",
  "SecretAccessKey": "...",
  "SessionToken": "..."
}
```
