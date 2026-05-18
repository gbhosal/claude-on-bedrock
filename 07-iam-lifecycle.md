# IAM User Lifecycle Management

This document covers how Terraform-managed IAM users are created, tagged, and deactivated as part of the long-term key strategy for AWS Bedrock access.

## Overview

Long-term IAM keys are the lowest-friction starting point when migrating from Anthropic Console, but they carry a governance risk: keys don't expire automatically. This document describes the controls that make them manageable until teams can adopt short-term credentials.

The three pillars are:
1. **Terraform ownership** — every IAM user is created and destroyed through code, not the console
2. **Consistent tagging** — five mandatory tags on every user answer "who owns this and why"
3. **LDAP-driven deactivation** — an automated tool cross-references `Individual` users against the corporate directory and disables keys when a person leaves

---

## IAM User Naming Conventions

| User type | IAM username format | Example |
|-----------|---------------------|---------|
| **Individual** (individual developer) | Exactly matches the person's LDAP/directory username | `jsmith` |
| **System** (LLM application) | App name, prefixed with `app-` | `app-ragbot-bedrock` |

Using the LDAP username directly eliminates the need for a separate mapping table — the LDAP sync tool can perform a simple set-difference.

---

## Mandatory Tags

All five tags below are **required** on every IAM user. Tag keys are **case-sensitive** — use exactly the casing shown.

| Tag key | Valid values | Purpose |
|---------|-------------|---------|
| `UserType` | `Individual` or `System` | Distinguishes humans from app service accounts; drives LDAP sync scope |
| `APPACCESS` | Free string (e.g. `claude-code`, `rag`, `codegen`) | Describes what the credentials are used to access |
| `GROUP` | Team name | Owning team for cost and accountability |
| `COSTCENTER` | Cost center code | Enables per-team cost allocation in AWS Cost Explorer |
| `Note` | Free text | Comments about the app team, owner, or anything relevant |

### Optional but strongly recommended

| Tag key | Format | Purpose |
|---------|--------|---------|
| `Contact` | Email address | Recipient for automated notifications (deactivation alerts, key rotation reminders) |

Terraform `validation` blocks in the module enforce that all five mandatory tags are non-empty and that `UserType` is exactly `Individual` or `System`. A `terraform plan` will fail fast if any mandatory tag is missing.

---

## Terraform Workflow

All IAM user management runs through the `terraform/` directory. See [CLAUDE.md](CLAUDE.md) for commands.

**To add a new Individual user**, add an entry to `developers` in your `terraform.tfvars`:

```hcl
developers = {
  "newuser" = {
    app_access  = "claude-code"
    group       = "myteam"
    cost_center = "CC-0001"
    note        = "New hire — platform team"
    contact     = "newuser@example.com"
  }
}
```

Then run `terraform apply`. The user is created with the Bedrock invoke policy attached and all tags set.

**To add a System user for an LLM app**, add an entry to `llm_apps` similarly, using the app name as the key.

**To remove a user** (e.g. permanent off-boarding or app decommission), delete the entry from `tfvars` and run `terraform apply`. This destroys the IAM user and detaches the policy. Before destroying, ensure any access keys have been deactivated.

---

## LDAP-Driven Key Deactivation

The automated LDAP sync tool targets only `UserType=Individual` users. `UserType=System` users are skipped — their lifecycle is managed by app decommission, not directory membership.

### How it works

1. List all IAM users with `UserType=Individual` tag
2. For each user, check if the IAM username exists in the LDAP/Identity directory
3. If the username is **not found** in LDAP (person has left the organization):
   - Call `aws iam update-access-key --status Inactive` for every active key on that user
   - Optionally send a notification to the `Contact` tag email
4. If the username **is found**, no action is taken

### Deactivation vs. deletion

Keys are **deactivated**, not deleted. The IAM user is also kept. This is intentional:

- CloudTrail audit history remains intact — you can trace what the user did after the fact
- Re-activation is possible if off-boarding was done in error (e.g. wrong LDAP sync, temporary contractor)
- Terraform remains the authoritative delete path; the sync tool only modifies key status

To permanently remove a user after off-boarding is confirmed, delete them from `terraform.tfvars` and run `terraform apply`.

### Recommended sync frequency

Run the LDAP sync at most **1 hour** after LDAP updates propagate. A longer window means a recently departed user's keys remain active. For high-sensitivity environments, consider also adding an IAM condition that denies API calls after a maximum key age:

```json
{
  "Condition": {
    "DateLessThan": {
      "aws:CurrentTime": "2026-12-31T00:00:00Z"
    }
  }
}
```

Or use a Service Control Policy (SCP) to enforce maximum key age org-wide.

---

## System User (App) Key Rotation

`System` users are not checked by the LDAP sync. Key rotation for app users must be triggered explicitly:

- **App decommission**: remove the entry from `llm_apps` in `terraform.tfvars` and apply
- **Key compromise**: immediately deactivate via `aws iam update-access-key --status Inactive`, then create a new key and update the app's secret store
- **Periodic rotation**: establish a rotation policy documented in the `Note` tag (e.g. `"Rotate every 90 days — see runbook"`)

The `Contact` tag should point to the app team's on-call or distribution list so rotation reminders reach the right people.

---

## Migration Trajectory

Long-term keys are a governed starting point, not a destination. The expected migration path:

| User type | Step 0 (now) | Step 1 (next quarter) | Step 2 (target) |
|-----------|-------------|----------------------|-----------------|
| **Individual** | Terraform IAM user + long-term key | AWS SSO / Identity Center login | SSO with short-lived tokens; no long-term keys |
| **System (app)** | Terraform IAM user + long-term key | STS `AssumeRole` from the app's deploy environment | EC2/ECS/Lambda instance role; no stored credentials |

See [02-credential-strategy.md](02-credential-strategy.md) for setup instructions for each auth method.

---

## Recommended Follow-On Controls

These are out of scope for this repo but worth implementing alongside this workflow:

- **SCP to enforce mandatory tags**: Deny `iam:CreateUser` and `iam:TagUser` unless all five mandatory tags are present. Prevents out-of-band user creation that bypasses Terraform.
- **SCP to enforce Terraform-only key creation**: Deny `iam:CreateAccessKey` for users without `ManagedBy=terraform` tag, or limit key creation to a dedicated pipeline role.
- **AWS Config rule**: Alert when an IAM user has an access key older than N days.
- **CloudTrail → CloudWatch alarm**: Alert on any `iam:CreateUser` event that originates outside your Terraform pipeline.
