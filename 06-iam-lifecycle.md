# IAM User Lifecycle Management

This document covers how Terraform-managed IAM users are created, tagged, and decommissioned for LLM application access to AWS Bedrock.

## Overview

Terraform's scope is **identity only**: it creates IAM users for LLM apps, attaches the Bedrock invoke policy, and enforces mandatory tags. It does **not** create Bedrock API keys, IAM access keys, or Secrets Manager entries — those credentials require rotation and are managed outside Terraform by the owning team.

The two pillars are:
1. **Terraform ownership** — every LLM app IAM user is created and destroyed through code, not the console
2. **Consistent tagging** — five mandatory tags on every user answer "who owns this and why"

---

## IAM User Naming Conventions

| User type | IAM username format | Example |
|-----------|---------------------|---------|
| **System** (LLM application) | App name, typically prefixed with `app-` | `app-ragbot-bedrock` |

Individual developer IAM users are **not** provisioned through this module. Use AWS SSO / Identity Center for local development (see [01-credential-strategy.md](01-credential-strategy.md#sso)).

---

## Mandatory Tags

All five tags below are **required** on every IAM user. Tag keys are **case-sensitive** — use exactly the casing shown.

| Tag key | Valid values | Purpose |
|---------|-------------|---------|
| `UserType` | `System` (fixed) | Identifies the account as an LLM application service account |
| `APPACCESS` | Free string (e.g. `rag`, `codegen`) | Describes what the credentials are used to access |
| `GROUP` | Team name | Owning team for cost and accountability |
| `COSTCENTER` | Cost center code | Enables per-team cost allocation in AWS Cost Explorer |
| `Note` | Free text | Comments about the app team, owner, or anything relevant |

### Optional but strongly recommended

| Tag key | Format | Purpose |
|---------|--------|---------|
| `Contact` | Email address | Recipient for rotation reminders and decommission notifications |

Terraform `validation` blocks in the module enforce that all five mandatory tags are non-empty. A `terraform plan` will fail fast if any mandatory tag is missing.

---

## Terraform Workflow

All IAM user management runs through the `terraform/` directory. See [CLAUDE.md](CLAUDE.md) for commands.

**To add an LLM app user**, add an entry to `llm_apps` in your `terraform.tfvars`:

```hcl
llm_apps = {
  "app-my-new-service" = {
    APPACCESS  = "rag"
    GROUP      = "myteam"
    COSTCENTER = "CC-0001"
    Note       = "New RAG service — staging"
    Contact    = "myteam-oncall@example.com"
  }
}
```

Then run `terraform apply`. The user is created with the Bedrock invoke policy attached and all tags set.

**To remove a user** (app decommission), delete the entry from `tfvars` and run `terraform apply`. Before destroying, deactivate any credentials issued to that user (Bedrock API keys, IAM access keys) through your credential management process.

---

## Credential Provisioning (Out of Band)

After `terraform apply` creates the IAM user, the app team provisions credentials separately. Terraform does not manage this step.

| Credential type | When to use | How to provision |
|-----------------|-------------|------------------|
| **Instance/task IAM role** | Production workloads on EC2, ECS, Lambda, EKS | Attach a role with the Bedrock policy; no keys on the user |
| **STS AssumeRole** | CI/CD, cross-account | Pipeline assumes a role; no keys stored on the user |
| **Bedrock API key** | Apps outside AWS (transitional) | Create in AWS console (Bedrock → API keys) or your org's key-rotation tooling; store in Secrets Manager via your rotation pipeline |
| **IAM access key** | Legacy integrations only | Create manually or via rotation tooling; **not** via Terraform |

Bedrock API keys and IAM access keys **must be rotated** on a schedule defined by the owning team (document in the `Note` tag or team runbook). Because rotation replaces secret material, these credentials cannot be safely managed as Terraform resources.

Example post-apply flow for a Bedrock API key:

1. `terraform apply` creates IAM user `app-ragbot-bedrock`
2. App team creates a Bedrock API key scoped to that user (console or internal tooling)
3. Key is stored in the app's Secrets Manager path (e.g. `myapp/bedrock/api-key`) by the rotation pipeline
4. Application reads `AWS_BEARER_TOKEN_BEDROCK` from the runtime secret injection mechanism

---

## App Decommission and Key Revocation

When an LLM app is retired:

1. **Revoke credentials first** — deactivate IAM access keys and revoke Bedrock API keys for the user
2. **Remove from Terraform** — delete the entry from `llm_apps` in `terraform.tfvars` and run `terraform apply`
3. **Verify** — confirm CloudTrail shows no further Bedrock invocations from the user

The `Contact` tag should point to the app team's on-call or distribution list so decommission and rotation reminders reach the right people.

---

## Migration Trajectory

| Stage | Identity (Terraform) | Credentials |
|-------|---------------------|-------------|
| **Now** | IAM user + Bedrock policy + tags | Bedrock API key or IAM access key, rotated out of band |
| **Next** | Same | STS `AssumeRole` from the app's deploy environment |
| **Target** | Retire IAM user; use instance/task role only | EC2/ECS/Lambda instance role; no stored credentials |

See [01-credential-strategy.md](01-credential-strategy.md) for setup instructions for each auth method.

---

## Recommended Follow-On Controls

These are out of scope for this repo but worth implementing alongside this workflow:

- **SCP to enforce mandatory tags**: Deny `iam:CreateUser` unless all five mandatory tags are present. Prevents out-of-band user creation that bypasses Terraform.
- **SCP to limit key creation**: Deny `iam:CreateAccessKey` except for a dedicated credential-rotation pipeline role.
- **AWS Config rule**: Alert when an IAM user has an access key older than N days.
- **CloudTrail → CloudWatch alarm**: Alert on any `iam:CreateUser` event that originates outside your Terraform pipeline.
