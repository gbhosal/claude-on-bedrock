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

### TypeScript / Node.js: Before vs After

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
import { AnthropicBedrock } from "@anthropic-ai/bedrock-sdk";

const client = new AnthropicBedrock({
  awsRegion: process.env.AWS_REGION ?? "us-east-1",
});

const message = await client.messages.create({
  model: "anthropic.claude-opus-4-7",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Hello" }],
});
```

**What changed:**
1. `@anthropic-ai/sdk` → `@anthropic-ai/bedrock-sdk`
2. `new Anthropic({ apiKey })` → `new AnthropicBedrock({ awsRegion })`
3. Model ID: `"claude-opus-4-7"` → `"anthropic.claude-opus-4-7"`
4. Everything else — `messages.create()`, streaming, tool use — is **identical**.

### Streaming: Before vs After

The streaming API is **identical** between direct Anthropic and Bedrock Mantle.

**Python:**
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

**Node.js:**
```javascript
import { AnthropicBedrock } from "@anthropic-ai/bedrock-sdk";

const client = new AnthropicBedrock({ awsRegion: "us-east-1" });

const stream = client.messages.stream({
  model: "anthropic.claude-opus-4-7",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Write a short story." }],
});

for await (const event of stream) {
  if (
    event.type === "content_block_delta" &&
    event.delta.type === "text_delta"
  ) {
    process.stdout.write(event.delta.text);
  }
}

const final = await stream.finalMessage();
console.log(final.usage);
```

### AWS Credentials for the SDK

The `AnthropicBedrockMantle` client uses the standard AWS SDK credential chain. For this organisation, applications typically authenticate with one of:

1. **`AWS_BEARER_TOKEN_BEDROCK`** — Bedrock API key (default for apps outside AWS or during migration)
2. **Instance/task IAM role** — when running on EC2, ECS, Lambda, or EKS (production target)
3. Constructor parameters or `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — only if your platform explicitly provisions IAM access keys

```python
from anthropic import AnthropicBedrockMantle

# Bedrock API key: set AWS_BEARER_TOKEN_BEDROCK + AWS_REGION
# Instance role: set AWS_REGION only (on AWS)
client = AnthropicBedrockMantle(aws_region="us-east-1")
```

**Node.js** uses the same credential chain. Set `AWS_BEARER_TOKEN_BEDROCK` or attach an instance role — no Anthropic API key constructor argument needed:

```javascript
import { AnthropicBedrock } from "@anthropic-ai/bedrock-sdk";

const client = new AnthropicBedrock({
  awsRegion: process.env.AWS_REGION ?? "us-east-1",
});
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

### Node.js with `@aws-sdk/client-bedrock-runtime`

Use the AWS SDK for JavaScript v3 when you can't install `@anthropic-ai/bedrock-sdk`:

```bash
npm install @aws-sdk/client-bedrock-runtime
```

**Non-streaming:**
```javascript
import {
  BedrockRuntimeClient,
  InvokeModelCommand,
} from "@aws-sdk/client-bedrock-runtime";

const client = new BedrockRuntimeClient({ region: "us-east-1" });

const response = await client.send(
  new InvokeModelCommand({
    modelId: "anthropic.claude-opus-4-7",
    contentType: "application/json",
    accept: "application/json",
    body: JSON.stringify({
      anthropic_version: "bedrock-2023-05-31",
      max_tokens: 1024,
      messages: [
        { role: "user", content: "Explain quantum entanglement." },
      ],
    }),
  })
);

const body = JSON.parse(new TextDecoder().decode(response.body));
console.log(body.content[0].text);
```

**Streaming:**
```javascript
import {
  BedrockRuntimeClient,
  InvokeModelWithResponseStreamCommand,
} from "@aws-sdk/client-bedrock-runtime";

const client = new BedrockRuntimeClient({ region: "us-east-1" });

const response = await client.send(
  new InvokeModelWithResponseStreamCommand({
    modelId: "anthropic.claude-opus-4-7",
    contentType: "application/json",
    body: JSON.stringify({
      anthropic_version: "bedrock-2023-05-31",
      max_tokens: 1024,
      messages: [{ role: "user", content: "Write a short story." }],
    }),
  })
);

for await (const event of response.body) {
  if (!event.chunk?.bytes) continue;
  const chunk = JSON.parse(new TextDecoder().decode(event.chunk.bytes));
  if (chunk.type === "content_block_delta") {
    const delta = chunk.delta ?? {};
    if (delta.type === "text_delta") {
      process.stdout.write(delta.text);
    }
  }
}
```

**Tool use** goes through the Converse API — see [`examples/nodejs/bedrock_direct.js`](examples/nodejs/bedrock_direct.js).

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

For the full list with SOL/EOL dates, see [04-model-lifecycle.md](04-model-lifecycle.md).

---

## Migrating Environment Variable Configuration

| Before | After |
|--------|-------|
| `ANTHROPIC_API_KEY=sk-ant-...` | Remove — not needed on Bedrock |
| — | `AWS_BEARER_TOKEN_BEDROCK=<bedrock-api-key>` (or instance role on AWS) |
| — | `AWS_REGION=us-east-1` |
| `ANTHROPIC_MODEL=claude-opus-4-7` | `ANTHROPIC_MODEL=anthropic.claude-opus-4-7` |

---

## Runnable Examples

**Python** — [`examples/python/`](examples/python/):
- [`basic_chat.py`](examples/python/basic_chat.py) — minimal hello world
- [`streaming.py`](examples/python/streaming.py) — streaming response
- [`tool_use.py`](examples/python/tool_use.py) — tool/function calling
- [`boto3_direct.py`](examples/python/boto3_direct.py) — raw boto3 approach

**Node.js** — [`examples/nodejs/`](examples/nodejs/):
- [`basic_chat.js`](examples/nodejs/basic_chat.js) — minimal hello world
- [`streaming.js`](examples/nodejs/streaming.js) — streaming response
- [`tool_use.js`](examples/nodejs/tool_use.js) — tool/function calling
- [`bedrock_direct.js`](examples/nodejs/bedrock_direct.js) — raw `@aws-sdk/client-bedrock-runtime` approach

```bash
# Node.js setup
cd examples/nodejs
npm install
export AWS_REGION=us-east-1
node basic_chat.js
node streaming.js
node tool_use.js
node bedrock_direct.js
```
