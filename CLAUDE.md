# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A migration guide and runnable examples for teams moving **LLM application code** from Anthropic's direct API to AWS Bedrock. There is no build system, test suite, or installable package — the deliverables are Markdown docs and copy-paste Python examples.

**Out of scope:** Claude Code CLI setup on Bedrock. Claude Code on Bedrock is strongly discouraged due to cost — see [README.md](README.md#do-not-use-claude-code-on-bedrock).

## Terraform (IAM User Lifecycle)

IAM users for LLM application Bedrock access are managed in `terraform/`. The module creates users, attaches the Bedrock invoke policy, and enforces all five mandatory tags. It does **not** create API keys or Secrets Manager secrets — credentials are provisioned and rotated outside Terraform.

```bash
cd terraform

# First-time setup
terraform init

# Preview changes
terraform plan -var-file=terraform.tfvars

# Apply (creates/updates/destroys users to match tfvars)
terraform apply -var-file=terraform.tfvars

# Validate HCL without AWS credentials
terraform validate
```

Copy `terraform.tfvars.example` to `terraform.tfvars` and fill in your users and apps. Never commit `terraform.tfvars` if it contains real usernames or internal cost center codes — add it to `.gitignore`.

## Running the Examples

**Python** — Anthropic SDK path:
```bash
pip install "anthropic[bedrock]"
```

For the boto3 path:
```bash
pip install boto3
```

Set credentials before running any example (from your app's secret store, SSO profile, or instance role — not from Terraform):

```bash
export AWS_REGION=us-east-1
export AWS_BEARER_TOKEN_BEDROCK=<bedrock-api-key>   # if using Bedrock API key auth
# or: export AWS_PROFILE=<sso-profile>
```

Run a Python example:
```bash
python examples/python/basic_chat.py
python examples/python/streaming.py
python examples/python/tool_use.py
python examples/python/boto3_direct.py
```

**Node.js** — Bedrock SDK path:
```bash
cd examples/nodejs
npm install
export AWS_REGION=us-east-1
export AWS_BEARER_TOKEN_BEDROCK=<bedrock-api-key>   # or AWS_PROFILE for SSO
node basic_chat.js
node streaming.js
node tool_use.js
node bedrock_direct.js
```

Check which Claude models are available in your account/region:
```bash
aws bedrock list-foundation-models \
  --by-provider Anthropic --region us-east-1 \
  --query 'modelSummaries[].{Name:modelName,ID:modelId,Status:modelLifecycle.status}' \
  --output table
```

## Architecture

### Two migration paths (see `03-sdk-migration.md`)

**Path A — Anthropic SDK with Bedrock backend (recommended):** Replace `Anthropic(api_key=...)` with `AnthropicBedrockMantle(aws_region=...)` and prefix model IDs with `anthropic.`. The entire `messages.create()` surface — including tool use, streaming, and extended thinking — is identical to the direct API. Notable exceptions: Batch API, Files API, server-side tools (Web Search, Code Execution), and Claude Managed Agents are **not available** on Bedrock.

**Path B — boto3 bedrock-runtime:** Lower-level. Requires manually constructing JSON bodies with `"anthropic_version": "bedrock-2023-05-31"` and parsing the response. Use `invoke_model` (non-streaming) or `invoke_model_with_response_stream`. Tool use goes through the Converse API.

### Model ID format

| Context | Direct Anthropic | Bedrock |
|---------|-----------------|---------|
| Model ID | `claude-opus-4-7` | `anthropic.claude-opus-4-7` |
| Production (cross-region) | N/A | `us.anthropic.claude-opus-4-7` |

Always use cross-region profiles (`us.*`, `eu.*`, `global.*`) in production — they route across regions automatically for higher availability.

### Active models (as of May 2026)

| Tier | Bedrock ID | Cross-Region Profile |
|------|-----------|----------------------|
| Opus 4.7 | `anthropic.claude-opus-4-7` | `us.anthropic.claude-opus-4-7` |
| Sonnet 4.6 | `anthropic.claude-sonnet-4-6` | `us.anthropic.claude-sonnet-4-6` |
| Haiku 4.5 | `anthropic.claude-haiku-4-5-20251001-v1:0` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |

Models with imminent EOL: Claude Opus 4 (May 31 2026), Claude 3.5 Haiku (Jun 19 2026), Claude 3 Sonnet (Jul 30 2026).

### Configuration templates (`examples/settings/`)

- `iam_policy.json` — minimal IAM policy to copy-paste

### Documentation index

| File | Topic |
|------|-------|
| `01-credential-strategy.md` | Auth methods for LLM apps: Terraform IAM users, STS, instance roles |
| `02-iam-permissions.md` | Minimal IAM policy, model access enablement, CI/CD policies |
| `03-sdk-migration.md` | Full before/after code for Path A and Path B (Python + TypeScript) |
| `04-model-lifecycle.md` | Model IDs, EOL dates, cross-region profiles, pinning versions in app code |
| `05-agentic-access.md` | Tool use, multi-turn loops, streaming, extended thinking, prompt caching |
| `06-iam-lifecycle.md` | Terraform-managed IAM users, mandatory tags, out-of-band credential provisioning |

## Editing Guidelines

When updating example code, always use cross-region profile model IDs (`us.anthropic.*`) in production-oriented snippets and plain `anthropic.*` IDs in minimal/introductory examples. Keep the feature parity table in `03-sdk-migration.md` current — Bedrock does not support Batch API, Files API, server-side tools, or Managed Agents. Do not add Claude Code CLI setup documentation — this repo is for LLM application workloads only.
