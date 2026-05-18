# Claude Code CLI Setup on AWS Bedrock

Claude Code (the `claude` CLI) can be configured to route all requests through AWS Bedrock instead of Anthropic's direct API. This requires no code changes — only configuration.

## Prerequisites

- AWS credentials configured (see [02-credential-strategy.md](02-credential-strategy.md))
- IAM permissions attached (see [03-iam-permissions.md](03-iam-permissions.md))
- Bedrock model access enabled in the AWS console for your region
- Claude Code installed: `npm install -g @anthropic-ai/claude-code`

---

## Option A: Interactive Wizard (Recommended for First-Time Setup)

Run the CLI and use the built-in setup wizard:

```bash
claude
```

At the login prompt:
1. Select **Use a third-party AI provider**
2. Select **Amazon Bedrock**
3. Follow prompts to:
   - Choose your AWS authentication method
   - Select your AWS region
   - Choose available Claude models from your account
   - Optionally pin specific model versions

The wizard saves your configuration to the `env` block in `~/.claude/settings.json` automatically.

---

## Option B: Manual Environment Variable Setup

Set these variables before running `claude`. This approach works for scripted or automated setups.

### Minimum required
```bash
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=us-east-1
```

> **Important**: Claude Code does **not** read `region` from `~/.aws/config`. You must explicitly set `AWS_REGION` as an environment variable.

### With specific auth method (pick one)

**SSO profile:**
```bash
export AWS_PROFILE=my-bedrock-profile
```

**Static keys:**
```bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**STS temporary keys:**
```bash
export AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=AQoXnyc4lcK4w...
```

**Bedrock API key:**
```bash
export AWS_BEARER_TOKEN_BEDROCK=your-bedrock-api-key
```

### Then launch
```bash
claude
```

---

## Option C: Persist Configuration in settings.json

Store your Bedrock config in `~/.claude/settings.json` so you don't need to export variables each session. This is the recommended approach for daily use.

### SSO profile with auto-refresh
```json
{
  "awsAuthRefresh": "aws sso login --profile my-bedrock-profile",
  "env": {
    "AWS_PROFILE": "my-bedrock-profile",
    "AWS_REGION": "us-east-1",
    "CLAUDE_CODE_USE_BEDROCK": "1"
  }
}
```

### Static keys (non-production only)
```json
{
  "env": {
    "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
    "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "AWS_REGION": "us-east-1",
    "CLAUDE_CODE_USE_BEDROCK": "1"
  }
}
```

Copy-paste templates: [examples/settings/settings_sso.json](examples/settings/settings_sso.json) and [examples/settings/settings_static_keys.json](examples/settings/settings_static_keys.json)

---

## Pinning Model Versions

By default, Claude Code resolves aliases like `sonnet` or `opus` to the latest model. When Anthropic releases a new model, the alias updates — which may break your setup if that model isn't yet available in your Bedrock account.

**Best practice for team deployments: always pin specific model version IDs.**

Add to `~/.claude/settings.json` → `env` block, or export as shell variables:

```bash
export ANTHROPIC_DEFAULT_OPUS_MODEL='us.anthropic.claude-opus-4-7'
export ANTHROPIC_DEFAULT_SONNET_MODEL='us.anthropic.claude-sonnet-4-6'
export ANTHROPIC_DEFAULT_HAIKU_MODEL='us.anthropic.claude-haiku-4-5-20251001-v1:0'
```

In `settings.json`:
```json
{
  "env": {
    "CLAUDE_CODE_USE_BEDROCK": "1",
    "AWS_REGION": "us-east-1",
    "AWS_PROFILE": "my-bedrock-profile",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "us.anthropic.claude-opus-4-7",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "us.anthropic.claude-sonnet-4-6",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
  }
}
```

For available model IDs and lifecycle status, see [05-model-lifecycle.md](05-model-lifecycle.md).

---

## Optional: Custom Endpoint and Region Overrides

```bash
# Override Bedrock endpoint (e.g., for VPC endpoints or custom domains)
export ANTHROPIC_BEDROCK_BASE_URL=https://bedrock-runtime.us-east-1.amazonaws.com

# Use a different region for the fast background model (Haiku) than the main model
export ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION=us-west-2

# Use an application inference profile ARN instead of a model ID
export ANTHROPIC_MODEL='arn:aws:bedrock:us-east-1:123456789012:application-inference-profile/my-profile-id'
```

---

## Optional: Prompt Caching

Claude Code uses 5-minute prompt cache TTL by default on Bedrock. To request a 1-hour TTL (if enabled on your account):

```bash
export ENABLE_PROMPT_CACHING_1H=1
```

To disable prompt caching entirely (useful for debugging):
```bash
export DISABLE_PROMPT_CACHING=1
```

---

## Verify the Setup

```bash
# Check Claude Code sees your Bedrock config
claude --print "What model are you running on? Respond in one sentence."
```

The response should confirm it's running on a Bedrock-hosted Claude model. If you see an auth error, revisit [02-credential-strategy.md](02-credential-strategy.md) and [03-iam-permissions.md](03-iam-permissions.md).
