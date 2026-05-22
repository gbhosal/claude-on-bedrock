# SDK Migration: Anthropic API → AWS Bedrock

This document covers the code changes required to move an LLM application from the direct Anthropic API to AWS Bedrock.

## Migration Paths

There are two approaches. Choose based on your constraints:

| Path | Best For | Code Change Size |
|------|----------|-----------------|
| **Path A: Anthropic SDK with Bedrock backend** | Teams already using `anthropic` SDK — minimal changes | Small (client init + model IDs) |
| **Path B: boto3 bedrock-runtime directly** | Teams that can't use the Anthropic SDK, or need fine-grained AWS control | Medium (request/response format changes) |

---

## Path A: Anthropic SDK with Bedrock Backend (Recommended)

The Anthropic SDK has a Bedrock variant that uses the same API surface. Switching requires changing only the client initialization and model ID strings.

### Install

```bash
# Python
pip install -U "anthropic[bedrock]"

# TypeScript / Node.js
npm install @anthropic-ai/bedrock-sdk

# Go
go get github.com/anthropics/anthropic-sdk-go/bedrock
```

### Python: Before vs After

**Before (direct Anthropic API):**
```python
import anthropic

client = anthropic.Anthropic(api_key="sk-ant-...")

message = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Explain quantum entanglement."}]
)
print(message.content[0].text)
```

**After (Bedrock — Mantle API, recommended):**
```python
from anthropic import AnthropicBedrockMantle

# No API key needed — uses AWS credential chain
client = AnthropicBedrockMantle(aws_region="us-east-1")

message = client.messages.create(
    model="anthropic.claude-opus-4-7",   # prefix changed: anthropic.
    max_tokens=1024,
    messages=[{"role": "user", "content": "Explain quantum entanglement."}]
)
print(message.content[0].text)
```

**What changed:**
1. `from anthropic import Anthropic` → `from anthropic import AnthropicBedrockMantle`
2. `Anthropic(api_key=...)` → `AnthropicBedrockMantle(aws_region="...")`
3. Model ID: `"claude-opus-4-7"` → `"anthropic.claude-opus-4-7"`
4. Everything else — `messages.create()`, response structure, tool use, streaming — is **identical**.

### TypeScript: Before vs After

**Before:**
```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const message = await client.messages.create({
  model: "claude-opus-4-7",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Hello" }],
});
```

**After:**
```typescript
import AnthropicBedrock from "@anthropic-ai/bedrock-sdk";

const client = new AnthropicBedrock({ awsRegion: "us-east-1" });

const message = await client.messages.create({
  model: "anthropic.claude-opus-4-7",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Hello" }],
});
```

### Streaming: Before vs After

The streaming API is **identical** between direct Anthropic and Bedrock Mantle:

```python
# Works the same on both direct API and Bedrock Mantle
with client.messages.stream(
    model="anthropic.claude-opus-4-7",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a short story."}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

### AWS Credentials for the SDK

The `AnthropicBedrockMantle` client uses the standard AWS SDK credential chain in this order:

1. `aws_access_key` / `aws_secret_key` constructor parameters
2. `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` environment variables
3. `~/.aws/credentials` named profile (`AWS_PROFILE` env var)
4. EC2/ECS instance metadata (when running inside AWS)

For SSO:
```python
# Ensure you've run: aws sso login --profile my-profile
client = AnthropicBedrockMantle(
    aws_region="us-east-1",
    # aws_profile="my-profile"  # or set AWS_PROFILE env var
)
```

---

## Path B: boto3 bedrock-runtime Directly

Use this path when you need lower-level control, can't install the Anthropic SDK, or are integrating with other AWS services in the same boto3 session.

### Install

```bash
pip install boto3
```

### Basic Invocation (Non-Streaming)

```python
import boto3
import json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

response = bedrock.invoke_model(
    modelId="anthropic.claude-opus-4-7",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": "Explain quantum entanglement."}
        ]
    }),
    contentType="application/json",
    accept="application/json"
)

body = json.loads(response["body"].read())
print(body["content"][0]["text"])
```

### Streaming with boto3

```python
import boto3
import json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

response = bedrock.invoke_model_with_response_stream(
    modelId="anthropic.claude-opus-4-7",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": "Write a short story."}]
    }),
    contentType="application/json"
)

for event in response["body"]:
    chunk = json.loads(event["chunk"]["bytes"])
    if chunk.get("type") == "content_block_delta":
        delta = chunk.get("delta", {})
        if delta.get("type") == "text_delta":
            print(delta.get("text", ""), end="", flush=True)
```

---

## API Feature Parity Table

| Feature | Direct Anthropic | Bedrock Mantle (AnthropicBedrockMantle) | Bedrock Legacy (boto3) |
|---------|-----------------|----------------------------------------|------------------------|
| Messages API | Yes | Yes | Via Converse API only |
| Streaming (SSE) | Yes | Yes (identical) | Bedrock event stream format |
| Tool use / function calling | Yes | Yes (identical) | Yes (via Converse API) |
| Extended thinking | Yes | Yes | Limited |
| Prompt caching | Yes | Yes | Limited |
| Vision / image input | Yes | Yes | Yes |
| System prompts | Yes | Yes | Yes |
| Multi-turn conversations | Yes | Yes | Yes |
| Batch API | Yes | **No** | **No** |
| Message Batches | Yes | **No** | **No** |
| Server-side tools (Web Search, Code Execution) | Yes | **No** | **No** |
| Claude Managed Agents | Yes | **No** | **No** |
| Files API | Yes | **No** | **No** |

## Model ID Format Changes

| Context | Direct Anthropic | Bedrock |
|---------|-----------------|---------|
| Latest Claude 4.7 Opus | `claude-opus-4-7` | `anthropic.claude-opus-4-7` |
| Sonnet 4.6 | `claude-sonnet-4-6` | `anthropic.claude-sonnet-4-6` |
| Haiku 4.5 | `claude-haiku-4-5-20251001` | `anthropic.claude-haiku-4-5-20251001-v1:0` |
| Cross-region profile (production) | N/A | `us.anthropic.claude-opus-4-7` |

For the full list with SOL/EOL dates, see [05-model-lifecycle.md](05-model-lifecycle.md).

---

## Migrating Environment Variable Configuration

| Before | After |
|--------|-------|
| `ANTHROPIC_API_KEY=sk-ant-...` | Remove — not needed on Bedrock |
| — | `AWS_ACCESS_KEY_ID=...` (or use SSO/instance role) |
| — | `AWS_REGION=us-east-1` |
| `ANTHROPIC_MODEL=claude-opus-4-7` | `ANTHROPIC_MODEL=anthropic.claude-opus-4-7` |

---

## Runnable Examples

See the [`examples/python/`](examples/python/) directory:
- [`basic_chat.py`](examples/python/basic_chat.py) — minimal hello world
- [`streaming.py`](examples/python/streaming.py) — streaming response
- [`tool_use.py`](examples/python/tool_use.py) — tool/function calling
- [`boto3_direct.py`](examples/python/boto3_direct.py) — raw boto3 approach
