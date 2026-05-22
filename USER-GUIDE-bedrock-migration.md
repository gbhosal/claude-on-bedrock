# User Guide: Using AWS Bedrock in Your LLM Application

**Audience:** Application developers migrating an LLM service from the Anthropic direct API to AWS Bedrock.

**Assumption:** Your platform team has already provisioned Bedrock access and delivered credentials to your app's secret store. This guide covers **how to wire those credentials into your application and update your code** — not how keys are created or rotated.

**Out of scope:** Claude Code (the `claude` CLI). Use an Anthropic subscription for interactive coding, not Bedrock.

---

## What changes for your app

| Before | After |
|--------|-------|
| `ANTHROPIC_API_KEY=sk-ant-...` | `AWS_BEARER_TOKEN_BEDROCK` + `AWS_REGION` |
| `anthropic.Anthropic(api_key=...)` | `AnthropicBedrockMantle(...)` (Python) or `AnthropicBedrock(...)` (Node.js) |
| Model ID: `claude-sonnet-4-6` | Model ID: `us.anthropic.claude-sonnet-4-6` |
| Endpoint: `api.anthropic.com` | Endpoint: AWS Bedrock (handled by the SDK) |

The **Messages API is the same** — streaming, tool use, extended thinking, and prompt caching work the same way once the client and model IDs are updated.

---

## Migration checklist (application team)

```
[ ] 1. Receive Bedrock credentials from platform team (secret store path documented)
[ ] 2. Inject AWS_BEARER_TOKEN_BEDROCK and AWS_REGION at runtime
[ ] 3. Replace Anthropic SDK client initialization
[ ] 4. Update all model ID strings to Bedrock format
[ ] 5. Pin production model IDs in app config
[ ] 6. Test in non-production
[ ] 7. Remove ANTHROPIC_API_KEY from all environments and config
[ ] 8. Deploy and confirm Bedrock traffic in CloudTrail
```

---

## Step 1 — Wire credentials into your application

Your Bedrock API key is delivered through your org's standard secret mechanism (e.g. AWS Secrets Manager, Kubernetes External Secrets, ECS task secrets, Lambda environment from Secrets Manager).

The SDK reads **`AWS_BEARER_TOKEN_BEDROCK`** automatically. You do not pass the key in code.

### Required runtime configuration

| Variable | Value |
|----------|-------|
| `AWS_BEARER_TOKEN_BEDROCK` | Bedrock API key from your secret store |
| `AWS_REGION` | Bedrock region (e.g. `us-east-1`) |

Use **`AWS_BEARER_TOKEN_BEDROCK`** exactly — not `AWS_BEARER_TOKEN`. That is the only env var name Bedrock SDKs recognize for API key auth.

### Kubernetes (example)

```yaml
env:
  - name: AWS_REGION
    value: "us-east-1"
  - name: AWS_BEARER_TOKEN_BEDROCK
    valueFrom:
      secretKeyRef:
        name: myapp-bedrock-credentials
        key: bedrock_api_key
```

### Docker / local `.env` (development only — never commit)

```bash
AWS_REGION=us-east-1
AWS_BEARER_TOKEN_BEDROCK=<value-from-your-dev-secret>
```

When the platform team rotates the key, they update the secret store. Your app picks up the new value on the next deploy or pod restart (depending on how secrets are mounted).

### What to remove

Delete `ANTHROPIC_API_KEY` from:

- Environment variables and Helm values
- CI/CD secret stores
- Application config files
- Any hardcoded references in code

---

## Step 2 — Update application code

### Python (recommended)

**Dependency:**
```bash
pip install -U "anthropic[bedrock]"
```

**Before:**
```python
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": user_message}],
)
text = response.content[0].text
```

**After:**
```python
import os
from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(
    aws_region=os.environ.get("AWS_REGION", "us-east-1"),
)

response = client.messages.create(
    model=os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"),
    max_tokens=1024,
    messages=[{"role": "user", "content": user_message}],
)
text = response.content[0].text
```

**Streaming** — same API, no other changes:
```python
with client.messages.stream(
    model="us.anthropic.claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": user_message}],
) as stream:
    for text in stream.text_stream:
        yield text
```

**Tool use** — `tools=`, `tool_use` stop reason, and `tool_result` messages are unchanged. See `examples/python/tool_use.py` in the migration repo.

---

### Node.js

**Dependency:**
```bash
npm install @anthropic-ai/bedrock-sdk
```

**Before:**
```javascript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const response = await client.messages.create({
  model: "claude-sonnet-4-6",
  max_tokens: 1024,
  messages: [{ role: "user", content: userMessage }],
});
```

**After:**
```javascript
import { AnthropicBedrock } from "@anthropic-ai/bedrock-sdk";

const client = new AnthropicBedrock({
  awsRegion: process.env.AWS_REGION ?? "us-east-1",
});

const response = await client.messages.create({
  model: process.env.BEDROCK_MODEL_ID ?? "us.anthropic.claude-sonnet-4-6",
  max_tokens: 1024,
  messages: [{ role: "user", content: userMessage }],
});
```

**Streaming:**
```javascript
const stream = client.messages.stream({
  model: "us.anthropic.claude-sonnet-4-6",
  max_tokens: 1024,
  messages: [{ role: "user", content: userMessage }],
});

for await (const event of stream) {
  if (event.type === "content_block_delta" && event.delta.type === "text_delta") {
    process.stdout.write(event.delta.text);
  }
}
```

See `examples/nodejs/` in the migration repo for complete runnable examples.

---

## Step 3 — Use the latest Claude model IDs

Bedrock model IDs are **not** the same strings as the direct Anthropic API. You must update every `model=` argument in your code.

### ID format rules

| Context | Format | Example |
|---------|--------|---------|
| Direct Anthropic API (old) | Short name, no prefix | `claude-sonnet-4-6` |
| Bedrock — single region (dev only) | `anthropic.<model>` | `anthropic.claude-sonnet-4-6` |
| Bedrock — **production (use this)** | Cross-region profile | `us.anthropic.claude-sonnet-4-6` |

**Production rule:** Always use **`us.anthropic.*`** cross-region profiles in deployed environments. They route across US regions automatically for higher availability and fewer throttling errors. Use plain `anthropic.*` IDs only for local smoke tests.

Haiku is the exception — its Bedrock ID includes a version suffix (`-v1:0`) on both regional and cross-region forms.

---

### Active models (May 2026) — use these for new work

| Tier | Model | Production model ID (copy this) | Regional ID (dev only) | Status |
|------|-------|--------------------------------|------------------------|--------|
| Most capable | **Claude Opus 4.7** | `us.anthropic.claude-opus-4-7` | `anthropic.claude-opus-4-7` | Active |
| Balanced (default) | **Claude Sonnet 4.6** | `us.anthropic.claude-sonnet-4-6` | `anthropic.claude-sonnet-4-6` | Active — EOL Oct 14, 2026 |
| Fast / low cost | **Claude Haiku 4.5** | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | `anthropic.claude-haiku-4-5-20251001-v1:0` | Active |

**Which model should I pick?**

| Your workload | Use | Production model ID |
|---------------|-----|---------------------|
| Classification, simple Q&A, high-volume routing | Haiku 4.5 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| RAG chatbots, general agents, most LLM features | Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6` |
| Complex reasoning, multi-step analysis, hard coding tasks | Opus 4.7 | `us.anthropic.claude-opus-4-7` |

If unsure, start with **Sonnet 4.6** — it is the default balanced choice for most LLM applications.

---

### Direct API → Bedrock mapping (migration reference)

If your code today uses the direct Anthropic API model name, map it like this:

| Direct Anthropic API (remove) | Bedrock production ID (use) |
|------------------------------|----------------------------|
| `claude-opus-4-7` | `us.anthropic.claude-opus-4-7` |
| `claude-sonnet-4-6` | `us.anthropic.claude-sonnet-4-6` |
| `claude-haiku-4-5-20251001` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |

Search your codebase for any remaining `claude-` model strings and replace them with the Bedrock ID from the table above.

---

### Cross-region profiles by geography

Use the profile that matches where your application runs:

**US (recommended for North America workloads):**
```
us.anthropic.claude-opus-4-7
us.anthropic.claude-sonnet-4-6
us.anthropic.claude-haiku-4-5-20251001-v1:0
```

**EU (data residency in Europe):**
```
eu.anthropic.claude-opus-4-7
eu.anthropic.claude-sonnet-4-6
```
*(Haiku 4.5 EU profile — confirm availability in your account with the CLI command below.)*

**Global (maximum geographic routing):**
```
global.anthropic.claude-opus-4-7
global.anthropic.claude-sonnet-4-6
```

---

### Deprecated models — migrate immediately if still in use

Do **not** deploy new workloads on these models. Update existing apps before the EOL date or requests will fail.

| Legacy model | EOL on Bedrock | Priority | Migrate to (production ID) |
|--------------|----------------|----------|----------------------------|
| Claude Opus 4 | **May 31, 2026** | Urgent | `us.anthropic.claude-opus-4-7` |
| Claude 3.5 Haiku | **Jun 19, 2026** | High | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| Claude 3 Sonnet | **Jul 30, 2026** | High | `us.anthropic.claude-sonnet-4-6` |
| Claude 3 Haiku | **Sep 10, 2026** | Medium | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |

---

### Pin model IDs in application config

Do not hardcode model strings in multiple files. Set them once via environment variables or Parameter Store:

```bash
# Primary model — most requests
export BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6

# Optional — fast/cheap model for routing, classification, or sub-tasks
export BEDROCK_FAST_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
```

**Python:**
```python
import os

DEFAULT_MODEL = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
FAST_MODEL = os.environ.get("BEDROCK_FAST_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
```

**Node.js:**
```javascript
const DEFAULT_MODEL = process.env.BEDROCK_MODEL_ID ?? "us.anthropic.claude-sonnet-4-6";
const FAST_MODEL = process.env.BEDROCK_FAST_MODEL_ID ?? "us.anthropic.claude-haiku-4-5-20251001-v1:0";
```

Update model IDs deliberately during planned migrations — not at runtime.

---

### Verify models available in your account

If a request fails with `ValidationException` on the model ID, confirm the model is enabled in your region:

```bash
aws bedrock list-foundation-models \
  --by-provider Anthropic \
  --region us-east-1 \
  --query 'modelSummaries[].{Name:modelName,ID:modelId,Status:modelLifecycle.status}' \
  --output table

aws bedrock list-inference-profiles \
  --region us-east-1 \
  --query 'inferenceProfileSummaries[?contains(inferenceProfileId, `anthropic`)]' \
  --output table
```

---

## Step 4 — Test your integration

**Smoke test with repo examples** (after setting env vars from your dev secret):

```bash
export AWS_REGION=us-east-1
export AWS_BEARER_TOKEN_BEDROCK=<from-your-dev-secret>

# Python
pip install "anthropic[bedrock]"
python examples/python/basic_chat.py

# Node.js
cd examples/nodejs && npm install && node basic_chat.js
```

**Verify in your app:**

1. A request completes with a valid response.
2. Token usage is returned in `response.usage`.
3. Streaming and tool-use paths still work if your app uses them.
4. No outbound calls to `api.anthropic.com` remain.

**Common errors:**

| Error | Likely cause |
|-------|--------------|
| `Could not load credentials` | `AWS_BEARER_TOKEN_BEDROCK` not set or empty string |
| `AccessDeniedException` | Key expired or revoked — request updated secret from platform team |
| `ValidationException` on model ID | Wrong model string — use `us.anthropic.*` cross-region profile |
| `ThrottlingException` | Rate limit — retry with backoff or contact platform team for quota |

---

## Feature compatibility

| Works on Bedrock (no code change beyond client + model ID) | Not available — requires redesign |
|-------------------------------------------------------------|-----------------------------------|
| Messages API | Batch API |
| Streaming | Files API |
| Tool use / function calling | Server-side tools (Web Search, Code Execution) |
| Extended thinking | Claude Managed Agents |
| Prompt caching | |
| Vision / image input | |

---

## Configuration reference

### Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `AWS_BEARER_TOKEN_BEDROCK` | Yes | Bedrock API key (from secret store) |
| `AWS_REGION` | Yes | AWS region for Bedrock runtime |
| `BEDROCK_MODEL_ID` | Recommended | Primary model — e.g. `us.anthropic.claude-sonnet-4-6` |
| `BEDROCK_FAST_MODEL_ID` | Optional | Fast/cheap model — e.g. `us.anthropic.claude-haiku-4-5-20251001-v1:0` |

### Variables to remove

| Variable | Action |
|----------|--------|
| `ANTHROPIC_API_KEY` | Remove everywhere |

---

## Further reading

| Topic | Location |
|-------|----------|
| Full SDK migration (Python, Node.js, boto3) | `03-sdk-migration.md` |
| Model EOL dates and cross-region profiles | `04-model-lifecycle.md` |
| Tool use, agents, streaming patterns | `05-agentic-access.md` |
| Runnable examples | `examples/python/`, `examples/nodejs/` |

For credential issues or a new secret after rotation, contact your platform team — do not create keys yourself.

---

*May 2026 — LLM applications only.*
