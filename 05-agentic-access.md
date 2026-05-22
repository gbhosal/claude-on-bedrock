# Agentic Access on AWS Bedrock

This document covers tool use (function calling), multi-turn agentic loops, streaming, and what differs between Bedrock and the direct Anthropic API for agentic workloads.

## Tool Use (Function Calling)

Tool use on the Bedrock Mantle API is **identical** to the direct Anthropic API. No code changes are needed beyond the client initialization changes described in [04-sdk-migration.md](04-sdk-migration.md).

### Defining and Calling Tools

```python
from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(aws_region="us-east-1")

tools = [
    {
        "name": "get_weather",
        "description": "Get current weather for a location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and state, e.g. 'Seattle, WA'"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit"
                }
            },
            "required": ["location"]
        }
    }
]

response = client.messages.create(
    model="anthropic.claude-opus-4-7",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "What's the weather in Seattle?"}]
)

# Check if Claude wants to call a tool
if response.stop_reason == "tool_use":
    for block in response.content:
        if block.type == "tool_use":
            print(f"Tool: {block.name}")
            print(f"Input: {block.input}")
            print(f"Tool call ID: {block.id}")
```

### Multi-Turn Agentic Loop

The pattern for a complete tool use round-trip is unchanged from the direct API:

```python
import json
from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(aws_region="us-east-1")

def get_weather(location: str, unit: str = "fahrenheit") -> str:
    # Replace with real weather API call
    return json.dumps({"temperature": 72, "condition": "sunny", "unit": unit})

def run_agent(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="anthropic.claude-opus-4-7",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        # Append assistant response to conversation
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Final text response — extract and return
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text

        elif response.stop_reason == "tool_use":
            # Execute tool calls and collect results
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "get_weather":
                        result = get_weather(**block.input)
                    else:
                        result = json.dumps({"error": f"Unknown tool: {block.name}"})

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Send tool results back to Claude
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "Agent loop ended unexpectedly"

print(run_agent("What's the weather in Seattle and New York?"))
```

## Streaming with Tool Use

Streaming tool use also works identically on Bedrock Mantle:

```python
from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(aws_region="us-east-1")

with client.messages.stream(
    model="anthropic.claude-opus-4-7",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "What's the weather in Seattle?"}]
) as stream:
    for event in stream:
        if event.type == "content_block_start":
            if hasattr(event.content_block, "type"):
                if event.content_block.type == "tool_use":
                    print(f"\nTool call: {event.content_block.name}")
        elif event.type == "content_block_delta":
            if hasattr(event.delta, "text"):
                print(event.delta.text, end="", flush=True)

    # Access the final message after streaming completes
    final_message = stream.get_final_message()
```

## Extended Thinking on Bedrock

Extended thinking (Claude's internal reasoning before responding) is supported on Bedrock:

```python
from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(aws_region="us-east-1")

response = client.messages.create(
    model="anthropic.claude-opus-4-7",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000  # tokens Claude can use for internal reasoning
    },
    messages=[{"role": "user", "content": "What is 27 * 453? Show your reasoning."}]
)

for block in response.content:
    if block.type == "thinking":
        print(f"[Thinking]: {block.thinking}")
    elif block.type == "text":
        print(f"[Answer]: {block.text}")
```

## Prompt Caching on Bedrock

Prompt caching reduces cost and latency for repeated large contexts (system prompts, documents, tool definitions). Supported on Bedrock Mantle.

```python
from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(aws_region="us-east-1")

large_document = "..." * 10000  # large repeated context

response = client.messages.create(
    model="anthropic.claude-opus-4-7",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": large_document,
            "cache_control": {"type": "ephemeral"}  # cache this block
        }
    ],
    messages=[{"role": "user", "content": "Summarize the document."}]
)

# Check cache usage in response
print(response.usage)
# Usage(input_tokens=100, cache_creation_input_tokens=50000, cache_read_input_tokens=0, output_tokens=200)
```

Default cache TTL on Bedrock is **5 minutes**. To request 1-hour TTL (if enabled on your account):
```bash
export ENABLE_PROMPT_CACHING_1H=1
```

---

## What Is NOT Available on Bedrock

These Anthropic API features are unavailable on Bedrock and require the direct Anthropic API:

| Feature | Direct Anthropic | Bedrock | Alternative |
|---------|-----------------|---------|------------|
| **Server-side Web Search** | Yes | No | Implement as a client tool using an external search API |
| **Server-side Web Fetch** | Yes | No | Implement as a client tool using `requests` or `httpx` |
| **Server-side Code Execution** | Yes | No | Implement as a client tool using a sandbox |
| **Claude Managed Agents** | Yes | No | Use Bedrock Agents (see below) or build your own loop |
| **Message Batches API** | Yes | No | Run requests concurrently with `asyncio` |
| **Files API** | Yes | No | Upload to S3 and pass content inline |
| `/v1/users` endpoint | Yes | No | N/A |

---

## Bedrock Agents (AWS-Native Orchestration)

If your use case requires managed orchestration — automatic prompt engineering, persistent memory, knowledge base integration, or action groups — AWS provides **Bedrock Agents** as a higher-level service.

Bedrock Agents differ from Claude's tool use in that AWS manages:
- Orchestration and routing across multiple steps
- Session memory across conversations
- Integration with Bedrock Knowledge Bases (RAG)
- Action groups (API invocations defined via OpenAPI schemas)
- Guardrails

**When to use Bedrock Agents vs. custom tool use loop:**

| Scenario | Use |
|----------|-----|
| Full control over the agent loop, custom routing | Custom tool use loop (this doc) |
| Need RAG with Bedrock Knowledge Bases | Bedrock Agents |
| Need persistent session memory managed by AWS | Bedrock Agents |
| Simple stateless tool use | Custom tool use loop |
| Enterprise orchestration with audit/trace | Bedrock Agents |

Bedrock Agents use the `boto3` `bedrock-agent-runtime` client:

```python
import boto3

agent_runtime = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

response = agent_runtime.invoke_agent(
    agentId="YOUR_AGENT_ID",
    agentAliasId="YOUR_AGENT_ALIAS_ID",
    sessionId="my-session-123",
    inputText="What are the top products by revenue this quarter?"
)

# Bedrock Agents return an event stream
for event in response["completion"]:
    if "chunk" in event:
        print(event["chunk"]["bytes"].decode(), end="", flush=True)
```

---

## Async Usage

For high-throughput agentic applications, use the async client:

```python
import asyncio
from anthropic import AsyncAnthropicBedrockMantle

async def run_parallel_agents(queries: list[str]):
    client = AsyncAnthropicBedrockMantle(aws_region="us-east-1")
    tasks = [
        client.messages.create(
            model="anthropic.claude-haiku-4-5-20251001-v1:0",
            max_tokens=512,
            messages=[{"role": "user", "content": q}]
        )
        for q in queries
    ]
    responses = await asyncio.gather(*tasks)
    return [r.content[0].text for r in responses]

results = asyncio.run(run_parallel_agents([
    "Summarize topic A",
    "Summarize topic B",
    "Summarize topic C",
]))
```

Note: Bedrock rate limits apply per-region. For batch workloads at scale, distribute across regions using cross-region inference profiles.
