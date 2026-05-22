# Anthropic → AWS Bedrock Migration Guide

This repo documents how to migrate **LLM application code** from Anthropic's direct API to AWS Bedrock. All guidance follows AWS and Anthropic best practices as of May 2026.

> **Scope:** This guide covers production and development workloads for LLM applications — chatbots, RAG pipelines, codegen services, batch inference, and SDK-integrated agents. It does **not** cover Claude Code (the `claude` CLI).

---

## Do Not Use Claude Code on Bedrock

**Claude Code routed through AWS Bedrock is strongly discouraged.** Use an Anthropic subscription (Pro, Max, Team, or Enterprise) or the direct Anthropic API with workspace spend limits instead.

### Why Claude Code on Bedrock is expensive

Bedrock charges the same per-token rates as the direct Anthropic API — there is no discount for agentic tooling. Claude Code's cost problem is **volume**, not rate:

| Factor | Impact |
|--------|--------|
| **Agentic context growth** | Every turn re-sends the full conversation history, tool outputs, and file contents. Input tokens grow with each message; a moderate 30-turn session can exceed 150K input tokens. |
| **Enterprise usage averages** | Anthropic reports ~**$13 per developer per active day** and **$150–250 per developer per month** for Claude Code API usage, with 90% of users below $30/active day. ([Claude Code cost docs](https://code.claude.com/docs/en/costs)) |
| **Agent teams** | Each teammate runs as a separate Claude instance with its own context window — approximately **7× more tokens** than a single session. ([Agent teams docs](https://code.claude.com/docs/en/agent-teams)) |
| **Extended thinking** | Reasoning tokens are billed as output tokens at the full output rate ($15–25/M for Sonnet/Opus). |
| **No Bedrock spend guardrails** | Claude Code workspace spend limits and rate-limit controls in the Anthropic Console do not apply when billing goes through AWS. Runaway agent sessions are harder to cap. |

### Illustrative cost examples (Bedrock on-demand, May 2026)

Per-million-token rates on Bedrock match the Anthropic API ([AWS Bedrock pricing](https://aws.amazon.com/bedrock/pricing/), [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)):

| Model | Input / 1M tokens | Output / 1M tokens |
|-------|-------------------|---------------------|
| Claude Sonnet 4.6 | $3.00 | $15.00 |
| Claude Opus 4.7 | $5.00 | $25.00 |
| Claude Haiku 4.5 | $1.00 | $5.00 |

**Single active developer, one Sonnet session (~400K input + 80K output tokens in a day):**
~$1.20 input + $1.20 output = **~$2.40/day** — below average, but still uncontrolled AWS spend with no subscription cap.

**Heavy agentic day (Opus, ~2M input + 400K output — agent teams or long autonomous runs):**
~$10.00 input + $10.00 output = **~$20/day per developer**.

**Team of 20 developers at Anthropic's reported average ($150–250/dev/month):**
**$3,000–5,000/month** on your AWS bill, allocated across cost centers but without Anthropic's workspace-level spend controls.

By contrast, a typical LLM application request (single-turn RAG query, ~4K input + 500 output on Haiku) costs **~$0.006 per request** — three orders of magnitude less per interaction than an agentic coding session.

### What to use instead

| Use case | Recommended approach |
|----------|---------------------|
| Interactive coding assistant | Claude Code with Anthropic Pro/Max/Team subscription (usage included) |
| Autonomous coding agents | Direct Anthropic API with workspace spend limits and rate caps |
| Production LLM features (chat, RAG, classification) | **AWS Bedrock** — this repo |

---

## Why Bedrock for LLM Applications?

| Benefit | Details |
|---------|---------|
| **Enterprise IAM** | Access control via AWS roles and policies — no shared API keys |
| **AWS billing** | Claude usage consolidated into your AWS bill with cost-center tags |
| **Regional data residency** | Keep inference traffic within specific AWS regions |
| **VPC integration** | Keep traffic on-network via VPC endpoints |
| **Audit logging** | CloudTrail captures all model invocations |
| **Cross-region resilience** | Inference profiles automatically route across regions |
| **Predictable unit economics** | Per-request costs are bounded by your application's prompt design |

## Prerequisites

1. **AWS account** with Bedrock access enabled (request access in the AWS console under Amazon Bedrock → Model access)
2. **AWS CLI v2** installed: `aws --version`
3. **Python 3.8+** or Node.js 18+ for SDK examples
4. **IAM user or role** with the permissions described in [02-iam-permissions.md](02-iam-permissions.md)

## Documentation Index

| Doc | What It Covers |
|-----|---------------|
| [01-credential-strategy.md](01-credential-strategy.md) | Auth methods for LLM apps: Terraform Bedrock API keys, STS, instance roles |
| [02-iam-permissions.md](02-iam-permissions.md) | Required IAM policy and resource scoping |
| [03-sdk-migration.md](03-sdk-migration.md) | Code changes: Anthropic SDK → Bedrock SDK |
| [04-model-lifecycle.md](04-model-lifecycle.md) | Which models to use, EOL dates, pinning versions in app code |
| [05-agentic-access.md](05-agentic-access.md) | Tool use, agents, streaming on Bedrock |
| [06-iam-lifecycle.md](06-iam-lifecycle.md) | Terraform-managed IAM users, mandatory tags, LDAP-driven key deactivation |

## Quick-Start Checklist

```
[ ] 1. Add your LLM app to terraform/terraform.tfvars (llm_apps block) and run terraform apply
       (creates the IAM user, attaches the Bedrock policy, generates a Bedrock API key,
        and saves it to Secrets Manager at iam/bedrock/<app-name>)
[ ] 2. Retrieve the Bedrock API key from Secrets Manager
[ ] 3. Update application code (see 03-sdk-migration.md)
[ ] 4. Pin model versions in application config (see 04-model-lifecycle.md)
[ ] 5. Choose the right model tier for your workload (Haiku for high-volume, Sonnet for balanced)
```

## Auth Method Decision Guide

```
Are you running inside AWS (EC2, ECS, Lambda)?
  └─ YES → Use instance/task IAM role (no credentials needed)
  └─ NO
       ├─ LLM application? (System)
       │    └─ Terraform-provisioned Bedrock API key, no expiry
       │         → terraform/terraform.tfvars (llm_apps block)
       │         → key stored at Secrets Manager: iam/bedrock/<app-name>
       │         → long-term path: migrate to instance/task IAM role
       ├─ Local SDK development / integration testing?
       │    └─ Terraform-provisioned Bedrock API key, 30-day rotation
       │         → terraform/terraform.tfvars (developers block)
       │         → key stored at Secrets Manager: iam/bedrock/<ldap-username>
       │         → for testing LLM app code only — NOT for Claude Code CLI
       ├─ CI/CD pipeline?
       │    └─ Use STS assumed-role (short-term keys) → see 01-credential-strategy.md#sts
       └─ Running inside AWS (EC2, ECS, Lambda)?
            └─ Use instance/task IAM role → see 01-credential-strategy.md#instance-role
```

## Key Lifecycle Management

The Terraform module in [`terraform/`](terraform/) provisions Bedrock API keys and stores them in Secrets Manager at `iam/bedrock/<name>`. Key governance rules:

| | Individual (local dev) | System (LLM app) |
|-|------------------------|------------------|
| **Purpose** | SDK integration testing only | Production and staging LLM workloads |
| **Key type** | Bedrock API key | Bedrock API key |
| **Expiry** | 30 days — auto-rotated by Terraform | None — decommission with the app |
| **Secret path** | `iam/bedrock/<ldap-username>` | `iam/bedrock/<app-name>` |
| **LDAP sync** | Yes — key disabled when user leaves org | No |
| **Long-term target** | AWS SSO / Identity Center | EC2/ECS/Lambda instance role |

All users carry five mandatory tags (`UserType`, `APPACCESS`, `GROUP`, `COSTCENTER`, `Note` — case-sensitive). An automated LDAP sync targets `UserType=Individual` users and disables their Bedrock API key when they are no longer found in the directory.

See [06-iam-lifecycle.md](06-iam-lifecycle.md) for the full workflow and migration trajectory toward short-term credentials.

## Examples

Ready-to-run code is in [`examples/`](examples/):

```
examples/
├── python/
│   ├── basic_chat.py       # Minimal AnthropicBedrockMantle hello world
│   ├── streaming.py        # Streaming text response
│   ├── tool_use.py         # Tool/function calling round-trip
│   └── boto3_direct.py     # Raw boto3 bedrock-runtime
├── nodejs/
│   ├── package.json        # @anthropic-ai/bedrock-sdk + AWS SDK deps
│   ├── basic_chat.js       # Minimal AnthropicBedrock hello world
│   ├── streaming.js        # Streaming text response
│   ├── tool_use.js         # Tool/function calling round-trip
│   └── bedrock_direct.js   # Raw @aws-sdk/client-bedrock-runtime
└── settings/
    └── iam_policy.json     # Copy-paste IAM policy
```
