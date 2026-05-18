# Anthropic → AWS Bedrock Migration Guide

This repo documents how to migrate Claude CLI (Claude Code) and LLM application code from Anthropic's direct API to AWS Bedrock. All guidance follows AWS and Anthropic best practices as of May 2026.

## Why Bedrock Instead of Direct Anthropic API?

| Benefit | Details |
|---------|---------|
| **Enterprise IAM** | Access control via AWS roles and policies — no shared API keys |
| **AWS billing** | Claude usage consolidated into your AWS bill |
| **Regional data residency** | Keep inference traffic within specific AWS regions |
| **VPC integration** | Keep traffic on-network via VPC endpoints |
| **Audit logging** | CloudTrail captures all model invocations |
| **Cross-region resilience** | Inference profiles automatically route across regions |

## Prerequisites

1. **AWS account** with Bedrock access enabled (request access in the AWS console under Amazon Bedrock → Model access)
2. **AWS CLI v2** installed: `aws --version`
3. **Python 3.8+** or Node.js 18+ for SDK examples
4. **Claude Code CLI** installed: `claude --version`
5. **IAM user or role** with the permissions described in [03-iam-permissions.md](03-iam-permissions.md)

## Documentation Index

| Doc | What It Covers |
|-----|---------------|
| [01-claude-cli-setup.md](01-claude-cli-setup.md) | Configure Claude Code CLI to use Bedrock |
| [02-credential-strategy.md](02-credential-strategy.md) | Short-term vs long-term keys, SSO, auto-refresh |
| [03-iam-permissions.md](03-iam-permissions.md) | Required IAM policy and resource scoping |
| [04-sdk-migration.md](04-sdk-migration.md) | Code changes: Anthropic SDK → Bedrock SDK |
| [05-model-lifecycle.md](05-model-lifecycle.md) | Which models to use, SOL/EOL dates |
| [06-agentic-access.md](06-agentic-access.md) | Tool use, agents, streaming on Bedrock |
| [07-iam-lifecycle.md](07-iam-lifecycle.md) | Terraform-managed IAM users, mandatory tags, LDAP-driven key deactivation |

## Quick-Start Checklist

```
[ ] 1. Add your user/app to terraform/terraform.tfvars and run terraform apply
       (this creates the IAM user, attaches the Bedrock policy, generates a
        Bedrock API key, and saves it to Secrets Manager at iam/bedrock/<name>)
[ ] 2. Retrieve your Bedrock API key from Secrets Manager
[ ] 3. Configure Claude Code CLI (see 01-claude-cli-setup.md)
[ ] 4. Update application code (see 04-sdk-migration.md)
[ ] 5. Pin model versions (see 05-model-lifecycle.md)
```

## Auth Method Decision Guide

```
Are you running inside AWS (EC2, ECS, Lambda)?
  └─ YES → Use instance/task IAM role (no credentials needed)
  └─ NO
       ├─ Individual developer? (Individual)
       │    └─ Terraform-provisioned Bedrock API key, 30-day rotation
       │         → terraform/terraform.tfvars (developers block)
       │         → key stored at Secrets Manager: iam/bedrock/<ldap-username>
       │         → long-term path: migrate to AWS SSO → see 02-credential-strategy.md#sso
       ├─ LLM application? (System)
       │    └─ Terraform-provisioned Bedrock API key, no expiry
       │         → terraform/terraform.tfvars (llm_apps block)
       │         → key stored at Secrets Manager: iam/bedrock/<app-name>
       │         → long-term path: migrate to instance/task IAM role
       ├─ CI/CD pipeline?
       │    └─ Use STS assumed-role (short-term keys) → see 02-credential-strategy.md#sts
       └─ Running inside AWS (EC2, ECS, Lambda)?
            └─ Use instance/task IAM role → see 02-credential-strategy.md#instance-role
```

## Key Lifecycle Management

The Terraform module in [`terraform/`](terraform/) provisions Bedrock API keys for all users and stores them in Secrets Manager at `iam/bedrock/<name>`. Key governance rules:

| | Individual (individual) | System (LLM app) |
|-|------------------------|------------------|
| **Key type** | Bedrock API key | Bedrock API key |
| **Expiry** | 30 days — auto-rotated by Terraform | None — decommission with the app |
| **Secret path** | `iam/bedrock/<ldap-username>` | `iam/bedrock/<app-name>` |
| **LDAP sync** | Yes — key disabled when user leaves org | No |
| **Long-term target** | AWS SSO / Identity Center | EC2/ECS/Lambda instance role |

All users carry five mandatory tags (`UserType`, `APPACCESS`, `GROUP`, `COSTCENTER`, `Note` — case-sensitive). An automated LDAP sync targets `UserType=Individual` users and disables their Bedrock API key when they are no longer found in the directory.

See [07-iam-lifecycle.md](07-iam-lifecycle.md) for the full workflow and migration trajectory toward short-term credentials.

## Examples

Ready-to-run code is in [`examples/`](examples/):

```
examples/
├── python/
│   ├── basic_chat.py       # Minimal AnthropicBedrockMantle hello world
│   ├── streaming.py        # Streaming text response
│   ├── tool_use.py         # Tool/function calling round-trip
│   └── boto3_direct.py     # Raw boto3 bedrock-runtime
└── settings/
    ├── settings_sso.json           # ~/.claude/settings.json for SSO
    ├── settings_static_keys.json   # ~/.claude/settings.json for static keys
    └── iam_policy.json             # Copy-paste IAM policy
```
