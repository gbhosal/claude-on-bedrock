# IAM User Lifecycle Management

This document covers how Terraform-managed IAM users are created, tagged, and decommissioned for LLM application access to AWS Bedrock.

## Overview

Terraform's scope is **identity only**: it creates IAM users for LLM apps, attaches the Bedrock invoke policy, and enforces mandatory tags. It does **not** create Bedrock API keys or Secrets Manager entries — keys are provisioned and rotated by the platform team.

The two pillars are:
1. **Terraform ownership** — every LLM app IAM user is created and destroyed through code, not the console
2. **Consistent tagging** — five mandatory tags on every user answer "who owns this and why"

---

## IAM User Naming Conventions

| User type | IAM username format | Example |
|-----------|---------------------|---------|
| **System** (LLM application) | App name, typically prefixed with `app-` | `app-ragbot-bedrock` |

Individual developer IAM users are **not** provisioned through this module. This Terraform workflow is for LLM application service accounts only.

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

**To remove a user** (app decommission), delete the entry from `tfvars` and run `terraform apply`. Before destroying, revoke any Bedrock API key issued to that user.

---

## Credential Provisioning (Out of Band)

After `terraform apply` creates the IAM user, the platform team provisions credentials separately. Terraform does not manage this step.

| Auth method | When to use | How to provision |
|-------------|-------------|------------------|
| **Bedrock API key** | Apps outside AWS; transitional | Platform team creates a key scoped to the IAM user; app stores in its secret store as `AWS_BEARER_TOKEN_BEDROCK` |
| **Instance/task IAM role** | Production workloads on EC2, ECS, Lambda, EKS (target) | Attach a role with the Bedrock policy; no stored keys |

Bedrock API keys **must be rotated** on a schedule defined by the platform team. Because rotation replaces secret material, keys cannot be safely managed as Terraform resources.

Example post-apply flow for a Bedrock API key:

1. `terraform apply` creates IAM user `app-ragbot-bedrock`
2. Platform team creates a Bedrock API key scoped to that user
3. Key is stored in the app's secret store (e.g. Secrets Manager path `myapp/bedrock/api-key`)
4. Application reads `AWS_BEARER_TOKEN_BEDROCK` from runtime secret injection

---

## App Decommission and Key Revocation

When an LLM app is retired:

1. **Revoke credentials first** — revoke the Bedrock API key for the user (or detach the instance role)
2. **Remove from Terraform** — delete the entry from `llm_apps` in `terraform.tfvars` and run `terraform apply`
3. **Verify** — confirm CloudTrail shows no further Bedrock invocations from the user

The `Contact` tag should point to the app team's on-call or distribution list so decommission and rotation reminders reach the right people.

---

## Migration Trajectory

| Stage | Identity (Terraform) | Credentials |
|-------|---------------------|-------------|
| **Now** | IAM user + Bedrock policy + tags | Bedrock API key (`AWS_BEARER_TOKEN_BEDROCK`), rotated out of band |
| **Target (AWS-hosted)** | Same IAM user, or retire user when role-only | Instance/task IAM role; no stored keys |

See [01-credential-strategy.md](01-credential-strategy.md) for setup instructions for each auth method.

---

## Recommended Follow-On Controls

These are out of scope for this repo but worth implementing alongside this workflow:

- **SCP to enforce mandatory tags**: Deny `iam:CreateUser` unless all five mandatory tags are present. Prevents out-of-band user creation that bypasses Terraform.
- **SCP to limit key creation**: Deny `iam:CreateAccessKey` except for a dedicated credential-rotation pipeline role.
- **AWS Config rule**: Alert when an IAM user has an access key older than N days.
- **CloudTrail → CloudWatch alarm**: Alert on any `iam:CreateUser` event that originates outside your Terraform pipeline.
