"""
Direct boto3 bedrock-runtime example (no Anthropic SDK required).

Use this approach when you need fine-grained AWS control or can't install
the anthropic[bedrock] package.

Prerequisites:
    pip install boto3
    export AWS_REGION=us-east-1
    export AWS_PROFILE=my-bedrock-profile
"""

import boto3
import json
import os

region = os.environ.get("AWS_REGION", "us-east-1")
bedrock = boto3.client("bedrock-runtime", region_name=region)

MODEL_ID = "anthropic.claude-opus-4-7"


# ── Non-streaming invocation ─────────────────────────────────────────────────

def invoke(prompt: str, max_tokens: int = 1024) -> str:
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }),
        contentType="application/json",
        accept="application/json"
    )
    body = json.loads(response["body"].read())
    return body["content"][0]["text"]


# ── Streaming invocation ─────────────────────────────────────────────────────

def invoke_streaming(prompt: str, max_tokens: int = 1024) -> str:
    response = bedrock.invoke_model_with_response_stream(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }),
        contentType="application/json"
    )

    full_text = []
    for event in response["body"]:
        chunk = json.loads(event["chunk"]["bytes"])
        chunk_type = chunk.get("type")
        if chunk_type == "content_block_delta":
            delta = chunk.get("delta", {})
            if delta.get("type") == "text_delta":
                text = delta.get("text", "")
                print(text, end="", flush=True)
                full_text.append(text)
        elif chunk_type == "message_stop":
            break

    print()  # newline after stream ends
    return "".join(full_text)


# ── Tool use via Converse API ─────────────────────────────────────────────────

def invoke_with_tools(prompt: str) -> str:
    """
    Tool use via the Converse API (boto3).
    The Converse API provides a unified interface for tool use across models.
    """
    tools = [
        {
            "toolSpec": {
                "name": "get_weather",
                "description": "Get current weather for a location.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "City name"}
                        },
                        "required": ["location"]
                    }
                }
            }
        }
    ]

    messages = [{"role": "user", "content": [{"text": prompt}]}]

    while True:
        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=messages,
            toolConfig={"tools": tools}
        )

        stop_reason = response["stopReason"]
        output_message = response["output"]["message"]
        messages.append(output_message)

        if stop_reason == "end_turn":
            for block in output_message["content"]:
                if "text" in block:
                    return block["text"]

        elif stop_reason == "tool_use":
            tool_results = []
            for block in output_message["content"]:
                if "toolUse" in block:
                    tool = block["toolUse"]
                    # Stub result — replace with real implementation
                    result_text = json.dumps({"temperature": 68, "condition": "cloudy"})
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool["toolUseId"],
                            "content": [{"text": result_text}]
                        }
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            return f"Unexpected stop reason: {stop_reason}"


if __name__ == "__main__":
    print("=== Non-streaming ===")
    result = invoke("What is the capital of France? One sentence.")
    print(result)

    print("\n=== Streaming ===")
    invoke_streaming("Write a two-sentence poem about AWS Bedrock.")

    print("\n=== Tool use (Converse API) ===")
    result = invoke_with_tools("What is the weather like in Paris?")
    print(result)
