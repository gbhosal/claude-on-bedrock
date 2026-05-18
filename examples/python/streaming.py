"""
Streaming response example using AnthropicBedrockMantle.

Prerequisites:
    pip install "anthropic[bedrock]"
    export AWS_REGION=us-east-1
    export AWS_PROFILE=my-bedrock-profile
"""

from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(aws_region="us-east-1")

print("Streaming response:\n")

with client.messages.stream(
    model="anthropic.claude-opus-4-7",
    max_tokens=512,
    messages=[
        {"role": "user", "content": "Write a three-sentence story about a developer who migrated to AWS Bedrock."}
    ]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

print("\n\n--- Final message stats ---")
final = stream.get_final_message()
print(f"Stop reason:   {final.stop_reason}")
print(f"Input tokens:  {final.usage.input_tokens}")
print(f"Output tokens: {final.usage.output_tokens}")
