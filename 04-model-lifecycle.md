# Claude Model Lifecycle on AWS Bedrock

## Recommended Models (Active as of May 2026)

These are the models to use for new workloads:

| Tier | Model | Bedrock Model ID | Cross-Region Profile | Status | EOL |
|------|-------|-----------------|----------------------|--------|-----|
| Most capable | Claude Opus 4.7 | `anthropic.claude-opus-4-7` | `us.anthropic.claude-opus-4-7` | **Active** | Not announced |
| Balanced | Claude Sonnet 4.6 | `anthropic.claude-sonnet-4-6` | `us.anthropic.claude-sonnet-4-6` | **Active** | Oct 14, 2026 |
| Fast / low cost | Claude Haiku 4.5 | `anthropic.claude-haiku-4-5-20251001-v1:0` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | **Active** | Not announced |

**Rule of thumb**: Use cross-region profiles (`us.*`) in production for higher availability and automatic failover across AWS regions.

## Models to Migrate Away From (Deprecated)

| Model | Legacy Since | Public Extended Access | **EOL Date** | Migrate To |
|-------|-------------|----------------------|-------------|------------|
| Claude Opus 4 | Oct 1, 2025 | Mar 1, 2026 | **May 31, 2026** | Claude Opus 4.7 |
| Claude 3.5 Haiku | Dec 19, 2025 | Mar 19, 2026 | **Jun 19, 2026** | Claude Haiku 4.5 |
| Claude 3 Sonnet | Jan 30, 2026 | Apr 30, 2026 | **Jul 30, 2026** | Claude Sonnet 4.6 |
| Claude 3 Haiku | Mar 10, 2026 | Jun 10, 2026 | **Sep 10, 2026** | Claude Haiku 4.5 |

> **Note**: Bedrock model lifecycle dates are AWS-specific and may differ from Anthropic's first-party API deprecation timeline.

## Lifecycle Stages Explained

| Stage | Meaning | Pricing Impact |
|-------|---------|---------------|
| **Active** | Fully supported, recommended for new deployments | Standard pricing |
| **Legacy** | Still works, 6+ month transition window before EOL | May increase during extended access |
| **Public Extended Access** | 3+ months before EOL, pay-as-you-go pricing at premium | Higher pricing applies |
| **EOL** | Model removed; requests fail after this date | N/A |

AWS guarantees at least **12 months** of availability from a model's launch date before it reaches EOL.

## Cross-Region Inference Profiles

Cross-region inference profiles distribute requests across multiple AWS regions automatically, improving availability and reducing throttling. Use these in production.

### US Geographic Profiles (recommended for North America)
```
us.anthropic.claude-opus-4-7
us.anthropic.claude-sonnet-4-6
us.anthropic.claude-haiku-4-5-20251001-v1:0
```

### Global Profiles
```
global.anthropic.claude-opus-4-7
global.anthropic.claude-sonnet-4-6
```

### EU Geographic Profiles
```
eu.anthropic.claude-opus-4-7
eu.anthropic.claude-sonnet-4-6
```

## Model Selection Guide

### For new projects
- **Complex reasoning, coding, analysis** → Claude Opus 4.7 (`us.anthropic.claude-opus-4-7`)
- **General-purpose, cost-balanced** → Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6`)
- **High-throughput, latency-sensitive, cost-sensitive** → Claude Haiku 4.5 (`us.anthropic.claude-haiku-4-5-20251001-v1:0`)

### For existing projects on Claude 3.x
| Currently Using | Migrate To | Priority |
|----------------|-----------|---------|
| Claude Opus 4 | Claude Opus 4.7 | **Urgent** — EOL May 31, 2026 |
| Claude 3.5 Haiku | Claude Haiku 4.5 | **High** — EOL Jun 19, 2026 |
| Claude 3 Sonnet | Claude Sonnet 4.6 | **High** — EOL Jul 30, 2026 |
| Claude 3 Haiku | Claude Haiku 4.5 | **Medium** — EOL Sep 10, 2026 |

## Pinning Model Versions in Application Code

Pin specific model IDs in your application configuration rather than relying on aliases or defaults. This prevents surprise breakage when Anthropic releases a new model version that may not yet be available in your Bedrock account, and makes cost attribution predictable.

**Environment variables (recommended for 12-factor apps):**
```bash
export BEDROCK_MODEL_ID='us.anthropic.claude-sonnet-4-6'
export BEDROCK_FAST_MODEL_ID='us.anthropic.claude-haiku-4-5-20251001-v1:0'
```

**Application config (Python example):**
```python
import os

DEFAULT_MODEL = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"
)
FAST_MODEL = os.environ.get(
    "BEDROCK_FAST_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
)
```

Deploy model IDs via your app's config management (Secrets Manager, Parameter Store, Helm values, etc.) and update them deliberately during model migrations — not at runtime.

## Checking Current Model Availability

List available models in your region via AWS CLI:
```bash
aws bedrock list-foundation-models \
  --by-provider Anthropic \
  --region us-east-1 \
  --query 'modelSummaries[].{Name:modelName,ID:modelId,Status:modelLifecycle.status}' \
  --output table
```

Check cross-region inference profiles:
```bash
aws bedrock list-inference-profiles \
  --region us-east-1 \
  --query 'inferenceProfileSummaries[?contains(inferenceProfileId, `anthropic`)]' \
  --output table
```
